# Omega Pure Handover Knowledge Base

This directory contains the critical handover state, architectural documentation, and engineering post-mortems for the Omega Pure project.

## 🔑 Core Documents (Must Read First)
*   **[`LATEST.md`](./LATEST.md)**: **The Single Source of Truth.** Current project phase, active blockers, emergency status, and immediate next steps.
*   **[`README.md`](../README.md)**: The high-level philosophy of V3 (Volume Clock, Spatial Restoration).

## 🛠️ Engineering & Infrastructure
*   **[`HARDWARE_TOPOLOGY.md`](./HARDWARE_TOPOLOGY.md)**: Physical nodes (Mac, Linux1, Windows1, GCP) and approved routing.
*   **[`ETL_ENGINEERING_LESSONS.md`](./ETL_ENGINEERING_LESSONS.md)**: Post-mortem on OOM deadlocks, CPU throttling, and Python performance anti-patterns encountered during the 2.2TB collapse.

## 📊 Methodology & Proving Grounds
*   **[`EXPERIMENTAL_DESIGN_AND_ROADMAP.md`](./EXPERIMENTAL_DESIGN_AND_ROADMAP.md)**: Mathematical derivation of physical constants (`vol_threshold`, `window_size`) and Phase 2-4 success criteria.
*   **[`V3_SMOKE_TEST_PLAN.md`](./V3_SMOKE_TEST_PLAN.md)**: Checklist for validating high-density V3 shards against GCP Vertex AI configurations.

## 🏛️ Legacy Archives
*   *Note: Phase 1 (Wall-Clock) and Phase 2 (Flattened Volume-Clock) documentation are retained in Git history but are deprecated for current operations.*
