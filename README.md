# RF Power Sweep and I–V Characterization Automation System

This project was developed during my internship at **DRDO – Solid State Physics Laboratory (SSPL), New Delhi**.  
It automates the testing and characterization process of semiconductor RF devices, replacing the traditional manual procedure with a fully integrated, software-driven workflow.

---

## 🧠 Project Overview

In conventional lab setups, measuring device characteristics like output power, gain, and efficiency required repetitive manual data recording and instrument configuration.  
This automation project streamlines the process by connecting all test instruments (signal generator, power meter, DC supply, etc.) through a unified Python interface.

The system performs **RF Power Sweep** and **I–V Characterization** tests with precise control, data acquisition, and visualization — reducing test time and minimizing human error.

---

## ⚙️ Core Functionality

- **Instrument Control:** Communication with lab instruments via **GPIB/USB** using the **PyVISA** library.  
- **RF Power Sweep:** Automatically varies input power and measures **Pout**, **Gain**, and **PAE (Power Added Efficiency)**.  
- **I–V Characterization:** Captures **voltage-current (V–I)** curves for different biasing conditions.  
- **Data Logging:** Stores all measured values in structured CSV files for later analysis.  
- **Plot Generation:** Automatically generates real-time plots of key parameters like Gain vs. Pin and PAE vs. Pin.  
- **User Interface:** Simple GUI interface to start, monitor, and save experiments.

---

## 🧩 Hardware Setup

- **Signal Generator:** Keysight EXG N5173B  
- **Power Meter:** NRP/NRX Power Meter (via GPIB)  
- **DC Power Supply:** Rohde & Schwarz NGP800 Series  
- **Device Under Test (DUT):** RF transistor wafer samples on probe station  

---

## 🖥️ Software Environment

- Python 3.11  
- Libraries: `PyVISA`, `pandas`, `matplotlib`, `tkinter`, `csv`  
- Tested on **Windows** and **Ubuntu** setups  
- Supports both local and LAN-connected instrument configurations

---

## 🚀 Results

| Test Type | Metric | Average Improvement |
|------------|---------|--------------------|
| RF Power Sweep | Test Time Reduction | **≈80% faster** |
| I–V Characterization | Data Consistency | **Fully reproducible curves** |
| Overall Accuracy | Error Margin vs Manual | **<2% deviation** |

The automated workflow provided consistent, high-quality measurement data while significantly improving throughput for device characterization.

---

## 📊 Typical Output Plots

- **Gain vs. Input Power (Pin)**  
- **Output Power (Pout) vs. Input Power (Pin)**  
- **Power Added Efficiency (PAE) vs. Pin**  
- **I–V Curve (Drain Current vs. Voltage)**  

These plots are automatically generated after each run and exported as `.png` and `.csv` files.

---

## 🧾 Project Outcome

The automation framework was successfully validated in the SSPL RF Device Lab and integrated into routine test operations.  
Its modular design allows easy extension for additional instruments or future wafer-level characterization setups.

---

## 🧑‍💻 Developed By

**Ganesh Maharaj Kamatham**  
Research Intern – DRDO SSPL (MAY-JULY 2025), New Delhi  
(Computer Science Engineering (Data Science), VIT Vellore)

---
