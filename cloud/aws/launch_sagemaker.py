"""Launch / check / fetch WiSpec training jobs on SageMaker (managed spot by default).

    pip install -r cloud/aws/requirements.txt
    export WISPEC_SM_ROLE=arn:aws:iam::<acct>:role/WiSpecSageMakerExecution
    export WISPEC_S3_BUCKET=<your-bucket>

    # synthetic smoke run (no upload), wait and print eval.json
    python cloud/aws/launch_sagemaker.py run --mode synthetic --wait

    # train on recorded sessions (uploads data/sessions to S3 first)
    python cloud/aws/launch_sagemaker.py run --mode data --data-dir data/sessions --wait

    python cloud/aws/launch_sagemaker.py status <job-name>
    python cloud/aws/launch_sagemaker.py fetch  <job-name> --out runs/<job-name>

Every command prints one machine-readable line starting with ``WISPEC_JOB``
so agents can parse the result.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import tarfile
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]


def _stage_source() -> str:
    """Copy only what the job needs (code + configs), not data/ or runs/."""
    d = Path(tempfile.mkdtemp(prefix="wispec_src_"))
    shutil.copytree(REPO / "wispec", d / "wispec", ignore=shutil.ignore_patterns("__pycache__"))
    shutil.copytree(REPO / "configs", d / "configs")
    shutil.copy(Path(__file__).parent / "sm_entry.py", d / "sm_entry.py")
    (d / "requirements.txt").write_text("")   # the PyTorch DLC already has torch + numpy
    return str(d)


def _emit(**kw):
    print("WISPEC_JOB " + json.dumps(kw))


def cmd_run(a):
    import sagemaker
    from sagemaker.pytorch import PyTorch

    role = a.role or os.environ["WISPEC_SM_ROLE"]
    bucket = a.bucket or os.environ["WISPEC_S3_BUCKET"]
    sess = sagemaker.Session(default_bucket=bucket)
    prefix = f"s3://{bucket}/wispec"

    inputs = None
    if a.mode == "data":
        if a.data_s3:
            inputs = {"training": a.data_s3}
        else:
            uri = sess.upload_data(a.data_dir, bucket=bucket, key_prefix="wispec/sessions")
            inputs = {"training": uri}

    est = PyTorch(
        entry_point="sm_entry.py",
        source_dir=_stage_source(),
        role=role,
        instance_type=a.instance_type,
        instance_count=1,
        framework_version=a.framework_version,
        py_version=a.py_version,
        use_spot_instances=not a.on_demand,
        max_run=a.max_hours * 3600,
        max_wait=(a.max_hours * 2 * 3600) if not a.on_demand else None,
        checkpoint_s3_uri=f"{prefix}/checkpoints/{a.tag}",
        output_path=f"{prefix}/output",
        base_job_name=f"wispec-{a.tag}",
        sagemaker_session=sess,
        hyperparameters={
            "mode": a.mode, "config": a.config, "sessions": a.sessions, "seconds": a.seconds,
            "stage1-epochs": a.stage1_epochs, "stage2-epochs": a.stage2_epochs, "stride": a.stride,
        },
        tags=[{"Key": "project", "Value": "wispec"}],
    )
    est.fit(inputs=inputs, wait=a.wait, logs="All" if a.wait else None)
    job = est.latest_training_job.name
    _emit(job=job, status="Completed" if a.wait else "InProgress", instance=a.instance_type,
          spot=not a.on_demand)
    if a.wait:
        a.job, a.out = job, a.out or str(REPO / "runs" / job)
        cmd_fetch(a)


def _describe(job: str) -> dict:
    import boto3
    return boto3.client("sagemaker").describe_training_job(TrainingJobName=job)


def cmd_status(a):
    d = _describe(a.job)
    _emit(job=a.job, status=d["TrainingJobStatus"], secondary=d.get("SecondaryStatus"),
          billable_seconds=d.get("BillableTimeInSeconds"), failure=d.get("FailureReason"))


def cmd_fetch(a):
    import boto3
    d = _describe(a.job)
    if d["TrainingJobStatus"] != "Completed":
        _emit(job=a.job, status=d["TrainingJobStatus"], failure=d.get("FailureReason"))
        return
    uri = d["ModelArtifacts"]["S3ModelArtifacts"]
    bucket, key = uri.removeprefix("s3://").split("/", 1)
    out = Path(a.out or REPO / "runs" / a.job)
    out.mkdir(parents=True, exist_ok=True)
    tgz = out / "model.tar.gz"
    boto3.client("s3").download_file(bucket, key, str(tgz))
    with tarfile.open(tgz) as t:
        t.extractall(out, filter="data")
    report = json.loads((out / "eval.json").read_text()) if (out / "eval.json").exists() else None
    _emit(job=a.job, status="Completed", out=str(out), billable_seconds=d.get("BillableTimeInSeconds"),
          eval=report)


def main(argv=None):
    p = argparse.ArgumentParser(prog="launch_sagemaker")
    sub = p.add_subparsers(dest="cmd", required=True)

    r = sub.add_parser("run")
    r.add_argument("--mode", choices=["synthetic", "data"], default="synthetic")
    r.add_argument("--config", default="configs/rig_tri_band.json")
    r.add_argument("--data-dir", default="data/sessions")
    r.add_argument("--data-s3", default=None, help="use sessions already in S3 instead of uploading")
    r.add_argument("--instance-type", default="ml.g4dn.xlarge")
    r.add_argument("--on-demand", action="store_true", help="disable managed spot")
    r.add_argument("--max-hours", type=int, default=4)
    r.add_argument("--framework-version", default="2.3")
    r.add_argument("--py-version", default="py311")
    r.add_argument("--sessions", type=int, default=8)
    r.add_argument("--seconds", type=float, default=150)
    r.add_argument("--stage1-epochs", type=int, default=30)
    r.add_argument("--stage2-epochs", type=int, default=40)
    r.add_argument("--stride", type=int, default=1)
    r.add_argument("--tag", default="dev", help="groups checkpoints in S3; reuse a tag to resume")
    r.add_argument("--role"); r.add_argument("--bucket")
    r.add_argument("--wait", action="store_true")
    r.add_argument("--out", default=None)

    s = sub.add_parser("status"); s.add_argument("job")
    f = sub.add_parser("fetch"); f.add_argument("job"); f.add_argument("--out", default=None)

    a = p.parse_args(argv)
    {"run": cmd_run, "status": cmd_status, "fetch": cmd_fetch}[a.cmd](a)


if __name__ == "__main__":
    main()
