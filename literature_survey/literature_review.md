# Literature Survey

## Satellite-AI Cloud Platform for Climate Risk and Flood Prediction

## Overview

A literature survey was conducted to understand recent advances in flood prediction using satellite imagery, artificial intelligence, remote sensing, cloud computing, and weather forecasting. Nine recent research papers (2023–2025) from reputed journals and conferences were reviewed to identify existing techniques, limitations, and research gaps.

---
#Papers reviewed

| Paper | Main Contribution | Research Gap |
|--------|-------------------|--------------|
| **Sarker, M. M., et al. (2024). _Vision Transformer for Flood Detection Using Satellite Images from Sentinel-1 and Sentinel-2_. Water, 16(12), 1670.** | Applies Vision Transformers to Sentinel-1 SAR and Sentinel-2 optical imagery for flood detection, capturing long-range spatial dependencies and outperforming CNN-based methods, especially in heterogeneous terrain. | Focuses only on image classification; does not integrate meteorological data, cloud deployment, real-time inference, or automated disaster response. |
| **Rindsfüser, N.; Zischg, A.P.; Keiler, M. (2024). _Monitoring Flood Risk Evolution: A Systematic Review_. iScience, 27(9), 110653.** | Systematic review synthesizing peer-reviewed literature on how land-use change, climate change, and socio-economic development drive the evolution of flood hazard, exposure, and vulnerability. | Purely a qualitative literature synthesis; lacks a standardized, quantitative, or real-time monitoring framework, and does not incorporate remote sensing or AI-based detection. |
| **Amitrano, D.; Di Martino, G.; Di Simone, A.; Imperatore, P. (2024). _Flood Detection with SAR: A Review of Techniques and Datasets_. Remote Sensing, 16(4), 656.** | Comprehensive review of SAR-based flood detection methods, datasets, and validation strategies, covering threshold-based, change-detection, and deep-learning approaches. | As a review, proposes no new model; highlights inconsistent validation practices and the absence of standardized, real-time operational pipelines. |
| **Mangukiya, N.K.; Kushwaha, S.; Sharma, A. (2024). _A Novel Multi-Model Ensemble Framework for Fluvial Flood Inundation Mapping_. Environmental Modelling & Software, 180, 106163.** | Proposes a multi-model ensemble combining flood extent and depth models using terrain conditioning factors, generalizing well to unforeseen fluvial flood events. | Does not integrate real-time satellite observation data or extend beyond fluvial floods; lacks deployment as an operational monitoring/early-warning tool. |
| **Li, Z.; Demir, I. (2023). _U-Net-Based Semantic Classification for Flood Extent Extraction Using SAR Imagery and GEE Platform: A Case Study for 2019 Central US Flooding_. Science of the Total Environment, 869, 161757.** | Modified U-Net model on Google Earth Engine extracts flood extent from Sentinel-1 SAR imagery, improved by fusing DEM, slope, and HAND terrain layers. | Validated on a single flood event/region only; no real-time or automated deployment, and no uncertainty quantification. |
| **Sharma, N.K.; Saharia, M. (2025). _DeepSARFlood: Rapid and Automated SAR-Based Flood Inundation Mapping Using Vision Transformer-Based Deep Ensembles with Uncertainty Estimates_. Science of Remote Sensing, 11, 100203.** | ViT-based deep ensemble tool achieving state-of-the-art IoU (0.72) on Sen1Floods11, processing 12,100 km² in under 40 seconds with pixel-level uncertainty estimates. | Not yet adapted for upcoming SAR missions (NISAR, Sentinel-1C); limited integration with weather forecasting for predictive, rather than reactive, mapping. |
| **Doan, T.-N.; Le-Thi, D.-N. (2025). _A Novel Deep Learning Model for Flood Detection from Synthetic Aperture Radar Images_. Journal of Advances in Information Technology, 16(1), 57–70.** | Deep learning change-detection model operating on bi-temporal SAR image pairs to rapidly and accurately identify flooded regions. | Requires both pre- and post-flood SAR acquisitions; limited discussion of continuous monitoring or generalization across terrains and sensors. |
| **Sanderson, J.; Mao, H.; Tengtrairat, N.; Al-Nima, R.; Woo, W. (2024). _Explainable Deep Semantic Segmentation for Flood Inundation Mapping with Class Activation Mapping Techniques_. ICAART 2024, Vol. 3, pp. 1028–1035.** | Dual encoder-decoder architecture outperforms DeepLabV3+ and U-Net++ on Sentinel-1/2 imagery, using Grad-CAM/HiResCAM to explain model decisions and improve trust. | Does not incorporate DEM/LiDAR topography, attention mechanisms, or automated multi-sensor fusion for real-time deployment. |
| **Garshasbi, M.; Alizadeh, H.; Mojaradi, B.; Saadatpour, M.; Zarei, E. (2025). _Uncertainty-Aware Flood Inundation Mapping with a Bayesian Deep Learning Framework Using SAR Imagery_. IEEE JSTARS, 18, 26716–26726.** | Bayesian deep learning framework generates probabilistic, pixel-wise flood maps with calibrated uncertainty, more efficient than physically-based hydrological models. | No integration with meteorological forecasting or optical/SAR fusion; limited exploration as a continuous, automated monitoring pipeline. |
## Overview

A literature survey was conducted to understand recent advances in flood prediction using satellite imagery, artificial intelligence, remote sensing, cloud computing, and weather forecasting. Eight recent research papers (2023–2026) from reputed journals were reviewed to identify existing techniques, limitations, and research gaps.

---

## Papers Reviewed

| Paper | Main Contribution | Research Gap |
|--------|-------------------|--------------|
| Flood Modeling and Prediction Using Earth Observation Data (2023) | Reviews Earth Observation data for flood modelling and prediction. | Lacks an integrated cloud-based platform for real-time prediction. |
| Automatic Flood Detection from Sentinel-1 Data Using a Nested UNet Model (2024) | Deep learning model for automatic flood detection using Sentinel-1 SAR imagery. | Does not integrate live weather data or cloud deployment. |
| Rapid Inundation Mapping Using the US National Water Model (2024) | Combines hydrological simulations and CNNs for flood mapping. | Limited to regional datasets and lacks cloud-native deployment. |
| Vision Transformer for Flood Detection (2024) | Uses Vision Transformers for satellite image classification. | Focuses only on image classification without real-time deployment. |
| Mapping Floods from Remote Sensing Data (2023) | Studies SAR and optical imagery for flood mapping. | No AI-driven prediction or cloud-based processing. |
| Deep Learning Applications for Flood Forecasting (2023) | Reviews deep learning techniques for flood forecasting. | Limited discussion on scalable cloud implementation. |
| Know to Predict, Forecast to Warn (2023) | Reviews flood prediction and warning methodologies. | Existing systems lack integrated cloud platforms and automation. |
| Earth Observation Data for Enhanced Flood Monitoring (2026) | Reviews recent advances in EO-based flood monitoring. | Does not provide a complete operational cloud solution. |

---

## Key Findings

- Most studies use satellite imagery (Sentinel-1 SAR and/or Sentinel-2 optical) as the primary data source for flood detection and mapping.
- Deep learning architectures such as CNNs, U-Net, U-Net++, DeepLabV3+, and Vision Transformers consistently improve flood detection and segmentation accuracy over classical threshold-based methods.
- Several studies combine remote sensing with terrain, hydrological, or Bayesian uncertainty models to improve robustness and generalization to unforeseen flood events.
- Explainable AI (XAI) techniques such as Grad-CAM and HiResCAM are emerging tools to improve trust and interpretability of deep learning flood models.
- Very few works integrate satellite imagery, weather APIs, artificial intelligence, cloud computing, dashboards, authentication, and automated alerts into a single deployable platform.
- Cloud-native, real-time architectures for continuous flood monitoring and early warning remain limited across the reviewed literature.

---
---

## Identified Research Gap

Existing research primarily focuses on developing accurate flood detection or prediction models in isolation. However, there is limited work on building an end-to-end cloud platform that continuously collects satellite imagery and weather data, performs AI-based flood prediction with uncertainty quantification, stores results, visualizes flood-risk information through an interactive dashboard, and provides automated notifications to users.
The literature survey revealed that:

- Most studies use satellite imagery for flood detection.
- Deep learning models such as CNNs, UNet, EfficientNet, and Vision Transformers improve prediction accuracy.
- Several studies combine remote sensing with hydrological models.
- Very few works integrate satellite imagery, weather APIs, artificial intelligence, cloud computing, dashboards, authentication, and automated alerts into a single deployable platform.
- Cloud-native architectures for continuous flood monitoring remain limited.

---

## Identified Research Gap

Existing research primarily focuses on developing accurate flood detection or prediction models. However, there is limited work on building an end-to-end cloud platform that continuously collects satellite imagery and weather data, performs AI-based flood prediction, stores results, visualizes flood-risk information through an interactive dashboard, and provides automated notifications to users.

---

## Proposed Solution

The proposed project, **Satellite-AI Cloud Platform for Climate Risk and Flood Prediction**, addresses these limitations by integrating:

- NASA–IEEE GRSS Flood Dataset
- OpenWeather API
- AWS cloud services
- Machine learning–based flood prediction
- Interactive web dashboard
- Secure user authentication
- Automated flood alerts
- Cloud monitoring and logging

---

## References

1. Sarker, M. M., et al. (2024). *Vision Transformer for Flood Detection Using Satellite Images from Sentinel-1 and Sentinel-2*. **Water**, 16(12), 1670. https://doi.org/10.3390/w16121670

2. Rindsfüser, N.; Zischg, A. P.; Keiler, M. (2024). *Monitoring Flood Risk Evolution: A Systematic Review*. **iScience**, 27(9), 110653. https://doi.org/10.1016/j.isci.2024.110653

3. Amitrano, D.; Di Martino, G.; Di Simone, A.; Imperatore, P. (2024). *Flood Detection with SAR: A Review of Techniques and Datasets*. **Remote Sensing**, 16(4), 656. https://doi.org/10.3390/rs16040656

4. Mangukiya, N. K.; Kushwaha, S.; Sharma, A. (2024). *A Novel Multi-Model Ensemble Framework for Fluvial Flood Inundation Mapping*. **Environmental Modelling & Software**, 180, 106163. https://doi.org/10.1016/j.envsoft.2024.106163

5. Li, Z.; Demir, I. (2023). *U-Net-Based Semantic Classification for Flood Extent Extraction Using SAR Imagery and GEE Platform: A Case Study for 2019 Central US Flooding*. **Science of the Total Environment**, 869, 161757. https://doi.org/10.1016/j.scitotenv.2023.161757

6. Sharma, N. K.; Saharia, M. (2025). *DeepSARFlood: Rapid and Automated SAR-Based Flood Inundation Mapping Using Vision Transformer-Based Deep Ensembles with Uncertainty Estimates*. **Science of Remote Sensing**, 11, 100203. https://doi.org/10.1016/j.srs.2025.100203

7. Doan, T.-N.; Le-Thi, D.-N. (2025). *A Novel Deep Learning Model for Flood Detection from Synthetic Aperture Radar Images*. **Journal of Advances in Information Technology**, 16(1), 57–70. https://doi.org/10.12720/jait.16.1.57-70

8. Sanderson, J.; Mao, H.; Tengtrairat, N.; Al-Nima, R. R. O.; Woo, W. L. (2024). *Explainable Deep Semantic Segmentation for Flood Inundation Mapping with Class Activation Mapping Techniques*. In **Proceedings of the 16th International Conference on Agents and Artificial Intelligence (ICAART 2024)** (Vol. 3, pp. 1028–1035). https://doi.org/10.5220/0012432300003636

9. Garshasbi, M.; Alizadeh, H.; Mojaradi, B.; Saadatpour, M.; Zarei, E. (2025). *Uncertainty-Aware Flood Inundation Mapping with a Bayesian Deep Learning Framework Using SAR Imagery*. **IEEE Journal of Selected Topics in Applied Earth Observations and Remote Sensing**, 18, 26716–26726. https://doi.org/10.1109/JSTARS.2025.3610403
Detailed summaries, research gap analysis, and APA references for all eight papers are available in the project report.
