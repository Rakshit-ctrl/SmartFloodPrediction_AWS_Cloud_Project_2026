# Dataset Documentation

## Overview

This project uses the **NASA–IEEE GRSS Data Fusion Contest Flood Dataset** along with real-time weather data from the **OpenWeather API** to support climate risk assessment and flood prediction.

## Primary Dataset

### NASA–IEEE GRSS Flood Dataset

The NASA–IEEE GRSS Data Fusion Contest Flood Dataset is a publicly available satellite imagery dataset developed for flood detection and disaster management research. It contains high-resolution satellite images with corresponding flood annotations, making it suitable for training and evaluating flood prediction models.

**Dataset Information**

- **Name:** NASA–IEEE GRSS Data Fusion Contest Flood Dataset
- **Source:** NASA & IEEE Geoscience and Remote Sensing Society (GRSS)
- **Data Type:** Satellite imagery with flood masks
- **Purpose:** Flood detection and flood mapping
- **Format:** Image tiles and annotation masks

## Weather Data

Real-time environmental information is obtained using the **OpenWeather API**.

The following weather parameters are used:

- Temperature
- Rainfall
- Humidity
- Wind Speed
- Atmospheric Pressure

These parameters are combined with satellite imagery to improve flood prediction accuracy.

## Dataset Sources

- NASA–IEEE GRSS Flood Dataset: https://ieee-dataport.org/competitions/grss-data-fusion-contest
- OpenWeather API: https://openweathermap.org/api

## Usage

The satellite imagery serves as the primary input for flood analysis, while weather data provides additional environmental context. Together, these datasets support climate risk assessment and intelligent flood prediction within the AWS cloud platform.