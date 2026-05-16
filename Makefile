# Makefile for SuperMarioVision

PYTHON = python
PIP = pip
VENV = venv

# Default target
all: help

help:
	@echo "SuperMarioVision - Makefile"
	@echo "---------------------------"
	@echo "install  : Install dependencies"
	@echo "collect  : Run data collector for gestures"
	@echo "train    : Train the gesture classifier"
	@echo "run      : Run the main game (Multimodal)"
	@echo "clean    : Remove temporary files"
	@echo "setup    : Install and prepare everything"

install:
	$(PIP) install -r requirements.txt

collect:
	$(PYTHON) CV_controller/data_collector.py

train:
	$(PYTHON) CV_controller/train_classifier.py

run:
	$(PYTHON) Game/main.py

clean:
	@if exist CV_controller\__pycache__ rmdir /s /q CV_controller\__pycache__
	@if exist Game\__pycache__ rmdir /s /q Game\__pycache__
	@if exist CV_controller\models rmdir /s /q CV_controller\models
	@if exist gesture_dataset.csv del gesture_dataset.csv
	@echo "Pulizia completata."

setup: install
	@echo "Ambiente configurato. Ora esegui 'make collect' e 'make train' per l'IA."

.PHONY: help install collect train run clean setup
