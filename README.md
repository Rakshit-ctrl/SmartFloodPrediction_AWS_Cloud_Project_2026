# Climate Risk and Smart Flood Prediction Using AWS Cloud

## Team Members

- Student 1: Rakshit Ashtputre
- Student 2: Prashast Jain

## Problem Statement

Floods are among the most destructive natural disasters, causing significant damage to infrastructure, agriculture, and human life. Traditional flood monitoring systems often lack real-time analysis and accurate prediction capabilities. This project aims to develop a cloud-based intelligent flood prediction system by integrating satellite imagery and real-time weather data to provide timely flood risk assessments and alerts.

## Objectives

- Develop a cloud-based flood prediction system using AWS.
- Integrate satellite imagery and real-time weather data.
- Predict flood-prone regions using intelligent data processing.
- Store and manage datasets and prediction results securely.
- Provide an interactive dashboard for visualization.
- Send notifications during high flood-risk situations.

## Proposed Architecture / Framework

The proposed system collects satellite imagery from the NASA–IEEE GRSS Flood Dataset and weather information from the OpenWeather API. Incoming requests are handled through Amazon API Gateway and processed by AWS Lambda functions. The processed data is stored in Amazon S3 and Amazon RDS. The web application is hosted using AWS Amplify and secured with Amazon Cognito. Amazon SNS delivers flood alerts to users, while Amazon CloudWatch continuously monitors the application's health and performance.

For the detailed architecture diagram, see:

- [Architecture Documentation](architecture/system_architecture.md)

## Technology Stack

- Amazon Web Services (AWS)
- Python
- AWS Lambda
- Amazon API Gateway
- Amazon S3
- Amazon RDS (MySQL)
- AWS Amplify
- Amazon Cognito
- Amazon SNS
- Amazon CloudWatch
- OpenWeather API

## Dataset Details

This project utilizes the **NASA–IEEE GRSS Data Fusion Contest Flood Dataset** for satellite-based flood detection and the **OpenWeather API** for obtaining real-time weather information such as rainfall, humidity, temperature, wind speed, and atmospheric pressure.

For detailed dataset information, see:

- [Dataset Documentation](dataset/dataset.md)

## Repository Structure

```
docs/
literature_survey/
architecture/
dataset/
results/
presentation/
references/
src/
    frontend/
    backend/
    ai_model/
    azure/
```

## Team Workflow

- `main` – Stable production branch
- `develop` – Integration branch
- `feature/student1` – Individual development branch for Rakshit
- `feature/student2` – Individual development branch for Prashast

## Status

Project setup completed.