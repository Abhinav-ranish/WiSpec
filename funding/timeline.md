# FURI Research Timeline: Dual-Band Wi-Fi Material Classification

**Duration:** 14 weeks (Spring 2027 semester, January–April 2027)
**Expected effort:** 10–12 hours/week

| Week | Phase | Tasks | Deliverables |
|------|-------|-------|---|
| 1 | **Setup & Planning** | Order hardware (Wi-Fi cards, router, materials). Set up lab workspace. Finalize material list. Read background papers on CSI extraction and Wi-Fi propagation. | Hardware ordered; 1–2 page project plan document; reading notes. |
| 2 | **Hardware Integration** | Receive hardware; install Intel AX210 in lab machine. Verify CSI logging driver (Linux 802.11 drivers). Set up controlled AP environment. | Functional Wi-Fi card with CSI capture working; test log files generated. |
| 3 | **Baseline Measurement Pipeline** | Implement RSSI-based measurement script (Python). Set up antenna positioning rig. Baseline measurements in free space (10 trials at varying distances). | RSSI measurement script; free-space baseline data (100+ samples, both bands). |
| 4 | **Phase 1 Pilot: RSSI** | Conduct RSSI measurements for concrete, wood, drywall, glass, brick (3 trials each at standardized distances). Compute differential attenuation ratio. Train Random Forest baseline classifier (RSSI features only). | Phase 1 dataset (~1 GB RSSI logs); classifier performance (accuracy, confusion matrix); brief technical note (1 page). |
| 5 | **Phase 2 CSI Setup** | Modify CSI logging to capture multi-band CSI frames. Implement CSI preprocessing pipeline (removing noisy frames, interpolating frequency grid). Collect test CSI samples across one material to debug. | CSI data format validated; preprocessing pipeline debugged; sample CSI dataset. |
| 6 | **Phase 2 Feature Engineering** | Design and implement dual-band differential features: per-subcarrier attenuation ratio, band-integrated power ratio, phase coherence across bands. Visualize features for each material. | Feature extraction module (Python/NumPy); feature visualization plots; feature description document. |
| 7 | **Phase 2 Data Collection (Part 1)** | Systematic CSI collection for first 3 materials (concrete, wood, drywall) at multiple distances and TX power levels. ~1,000 frames per material. | CSI dataset for 3 materials (~3 GB); preliminary feature statistics (mean, variance by material). |
| 8 | **Phase 2 Data Collection (Part 2)** | Complete CSI collection for remaining materials (glass, brick, metal, free space). Augment with distance/environment variations. | Complete CSI dataset (all 7 conditions, ~5 GB); data quality assessment. |
| 9 | **Phase 2 Classifier Development** | Implement three classifiers: Random Forest, SVM (RBF kernel), shallow CNN (3-layer 1D conv). Train on 80% of data with 10-fold cross-validation. Tune hyperparameters. | Trained models for each classifier; cross-validation curves; hyperparameter log. |
| 10 | **Phase 2 Ablation & Evaluation** | Run ablation study: single-band RSSI, single-band CSI, dual-band RSSI, dual-band CSI. Compare accuracy, precision, recall, F1 per material. Statistical significance testing. | Ablation study results (table & plots); confusion matrices for best model; statistical test results (p-values). |
| 11 | **Analysis & Investigation** | Identify misclassified pairs (which materials confused?). Investigate failure modes (material thickness, moisture, multipath, etc.). Plot decision boundaries (2D projections). | Failure analysis document (1–2 pages); visualizations of confused pairs; hypotheses for future work. |
| 12 | **Documentation & Open Source** | Clean and annotate code; prepare dataset for release. Document measurement protocol, feature definitions, ML pipeline. Create GitHub repo with README. | GitHub repository with code, dataset, README, and license; clean codebase. |
| 13 | **Paper Writing** | Draft 4–6 page workshop paper following ACM SenSys format: abstract, intro, related work, method, results, discussion, conclusion. Incorporate advisor feedback. | First draft of workshop paper; figures and tables finalized. |
| 14 | **Final Submission & Closeout** | Revise paper based on feedback. Submit to target workshop (ACM SenSys or IEEE SECON). Archive final codebase and dataset. Write summary of work and lessons learned. | Submitted workshop paper; project summary document; final code/data snapshot. |

## Key Milestones

- **End of Week 4:** Phase 1 complete; RSSI baseline established.
- **End of Week 10:** Phase 2 complete; dual-band > single-band confirmed.
- **End of Week 12:** Open-source artifacts released; code documented.
- **End of Week 14:** Paper submitted; project concluded.

## Notes

- **Contingency:** If hardware delays occur, Weeks 1–2 can shift forward without impacting later phases. Weeks 4–10 are critical path.
- **Collaboration:** Advising professor to review interim results at end of Weeks 4, 10, and 13.
- **Data Management:** All raw data and logs backed up weekly to lab storage.
- **Publication Plan:** Target workshop paper submission by end of Week 14 (late April 2027). Allows for journal submission in summer if results warrant it.
