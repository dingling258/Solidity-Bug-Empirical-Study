# SolBugMiner: An Empirical Study on Bug Characteristics in Solidity Smart Contracts

This repository contains the replication package for our research paper. It includes the dataset of **624 real-world smart contract defects**, the **SolBugMiner** tool scripts, and the statistical analysis data used to derive our findings.

## 📂 Repository Structure

- **`data.xlsx`**: The core dataset containing the manually labeled metadata for **624 defects** collected from 16 representative Solidity projects. The metadata includes:
  - Defect Types (Taxonomy)
  - Fix Complexity Metrics
  - Functional Modules
  - Detection Mechanisms
  - Links to original PRs and Commits
- **`scripts/`**: Python scripts used for data mining and defect collection.
  - **Project-Specific Collectors**: Scripts named like `*_pr_collector.py` (e.g., `The_Graph_merged_pr_collector.py`, `zkSync_pr_collector.py`) are designed to mine PRs and commits from specific GitHub repositories.
  - **Defect Scanners**: Scripts named like `*_defect_scanner.py` help identify potential bug-fix patterns.
  - **`output/`**: This folder contains the generated `.xlsx` files for each individual project after running the scripts.
  - **`data/`**: Intermediate data storage.
- **`config/`**: Configuration files used to set up the mining parameters (e.g., GitHub API tokens, repository lists).

## 🔍 Key Findings

Our study reveals a paradigm shift in smart contract quality assurance:
1.  **Defect Landscape**: Traditional DASP vulnerabilities (e.g., Reentrancy) now account for only **18.3%** of defects. The landscape is dominated by **Development Toolchain Issues (18.6%)**, **State Inconsistency (16.3%)**, and **Standard Compliance Issues (14.6%)**.
2.  **Detection Blind Spots**: There is minimal overlap (<5.2%) between different detection mechanisms. Automated tools currently miss 99% of State Inconsistency issues.
3.  **Fix Complexity**: Fixes for standard compliance often require deep specification understanding despite small code changes, while state inconsistency issues require systemic cross-contract refactoring.

## 🚀 Usage

### 1. Prerequisites
Ensure you have Python 3.8+ installed. You will need the following dependencies:

```bash
pip install pandas openpyxl requests

(Note: If you have a requirements.txt, you can install via pip install -r requirements.txt)

2. Configuration
Before running the collectors, check the config/ folder to ensure any necessary API keys (e.g., GitHub Personal Access Token) are configured to avoid rate limits.

3. Running the Scripts
The scripts are modularized by project. You can run a collector for a specific project to generate its dataset.

Example 1: Verify Environment

bash
python scripts/test_environment.py

Example 2: Collect Data for "The Graph"

bash
python scripts/The_Graph_merged_pr_collector.py

Example 3: Collect Data for "zkSync"

bash
python scripts/zkSync_pr_collector.py

The results will be saved in the scripts/output/ directory as Excel files.

⚖️ License
This dataset and code are released for academic research purposes.
