# Handover Directory

This directory contains the critical handover state, ongoing architectural documentation, and historical post-mortems for the Omega Pure and Omega_vNext projects. 

## Core Documents
*   **[`LATEST.md`](./LATEST.md)**: The **SINGLE SOURCE OF TRUTH** for the current workspace state. Any new AI Agent or human operator MUST read this file first before taking any action. It contains the current phase, active blockers, and immediate next steps.
*   **[`HARDWARE_TOPOLOGY.md`](./HARDWARE_TOPOLOGY.md)**: Canonical definition of the physical nodes (Mac, Linux1, Windows1, GCP) and their approved SSH routing paths.
*   **[`EXPERIMENTAL_DESIGN_AND_ROADMAP.md`](./EXPERIMENTAL_DESIGN_AND_ROADMAP.md)**: Defines the mathematical and statistical experiments used to derive physical constants, explains the current data ETL process, and lays out the success criteria for the upcoming GCP HPO and backtesting phases.

## Engineering Lessons & Post-Mortems
*   **[`ETL_ENGINEERING_LESSONS.md`](./ETL_ENGINEERING_LESSONS.md)**: A deep-dive post-mortem regarding the 2.2TB Volume Clock ETL pipeline. It details critical failures and solutions regarding Linux `cgroup` OOM deadlocks, systemd slice CPU throttling, and Python/Pandas performance anti-patterns. **Highly recommended reading for any Agent tasked with heavy data processing on the Linux node.**
