# Training on AWS (SageMaker, using AWS credits)

The capture rig only records. All training runs as **SageMaker training
jobs**:

- **Billed per second only while a job runs.** No idle GPU box to forget about.
- **Managed spot by default.** Typically far cheaper than on-demand. Jobs
  checkpoint to S3 and resume automatically if spot capacity is reclaimed,
  and slower turnaround is fine for agent-driven testing.
- **Agent-friendly.** An agent can start the `SageMaker training` GitHub
  workflow, wait, and read `eval.json` from the run summary/artifact.
  Nobody needs AWS keys in a chat or a cloud session.

> AWS promotional credits normally cover SageMaker, EC2 and S3, but not
> AWS Marketplace purchases. Check your credit terms in the Billing console.

## Instance choice

The models are small. A 16–24 GB GPU is plenty for now.

| Instance | GPU | Use |
|----------|-----|-----|
| `ml.g4dn.xlarge` (default) | T4 16 GB | Cheapest GPU; fine for current models and synthetic runs |
| `ml.g5.xlarge` | A10G 24 GB | ~2–3× faster; bigger models / longer windows |
| `ml.g6.xlarge` | L4 24 GB | Similar to g5, often cheaper where available |
| `ml.m5.xlarge` | none | CPU-only smoke tests if GPU quota isn't approved yet |

Check current prices for your region on the SageMaker pricing page. Spot
training is billed at the spot rate. `BillableTimeInSeconds` is printed by
`launch_sagemaker.py status`.

## One-time setup

1. **Request quota** (Service Quotas → Amazon SageMaker): "ml.g4dn.xlarge for
   spot training job usage" (and g5 if wanted). New accounts start at 0, and
   approval can take a day, so do this first.
2. **S3 bucket** for data, checkpoints and outputs, e.g. `wispec-<account-id>`.
3. **SageMaker execution role** (the role the job runs as): trusted by
   `sagemaker.amazonaws.com`, with `AmazonSageMakerFullAccess` and read/write
   on the bucket. Note its ARN.
4. **Run from your machine** (optional):
   ```bash
   pip install -r cloud/aws/requirements.txt
   export WISPEC_SM_ROLE=arn:aws:iam::<acct>:role/<execution-role>
   export WISPEC_S3_BUCKET=<bucket>
   python cloud/aws/launch_sagemaker.py run --mode synthetic --wait
   ```
5. **Run from GitHub Actions / agents** (recommended):
   1. IAM → Identity providers → add OpenID Connect provider
      `token.actions.githubusercontent.com`, audience `sts.amazonaws.com`.
   2. Create a role for GitHub with a trust policy limited to this repo:
      ```json
      {
        "Effect": "Allow",
        "Principal": {"Federated": "arn:aws:iam::<acct>:oidc-provider/token.actions.githubusercontent.com"},
        "Action": "sts:AssumeRoleWithWebIdentity",
        "Condition": {
          "StringEquals": {"token.actions.githubusercontent.com:aud": "sts.amazonaws.com"},
          "StringLike": {"token.actions.githubusercontent.com:sub": "repo:Abhinav-ranish/WiSpec:*"}
        }
      }
      ```
      Give it: `sagemaker:CreateTrainingJob`, `sagemaker:DescribeTrainingJob`,
      `sagemaker:AddTags`, `logs:GetLogEvents`, `logs:DescribeLogStreams`,
      `iam:PassRole` on the execution role only, and S3 read/write on the bucket.
   3. Repo → Settings → Secrets and variables → Actions: secrets
      `AWS_ROLE_ARN` (the GitHub role), `WISPEC_SM_ROLE` (execution role),
      `WISPEC_S3_BUCKET`; variable `AWS_REGION`.
   4. Actions → "SageMaker training" → Run workflow. Results appear in the run
      summary and the `wispec-eval` artifact.
6. **Set a budget alarm** (Billing → Budgets) so credits can't silently
   run out.

## Recorded data

```bash
# upload once, then reuse the S3 URI for every run
python cloud/aws/launch_sagemaker.py run --mode data --data-dir data/sessions --wait
# later runs / workflow input `data_s3`:
python cloud/aws/launch_sagemaker.py run --mode data --data-s3 s3://<bucket>/wispec/sessions --wait
```

Upload the converted `.npz` sessions, not the raw PicoScenes `.csi` files.
They're what training reads, and they're smaller.

## Body tracking

Joint labels come from the Femto Bolt via the Azure Kinect Body Tracking
SDK. It can run on the capture PC in CPU mode, which is slow but free, or
batch-processed on a GPU instance later. No GPU is needed on the capture
PC.
