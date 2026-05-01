TCGA-PAAD Test Sample
=====================

File
----
TCGA-HZ-7926-01Z-00-DX1.b3bf02d3-bad0-4451-9c39-b0593f19154c.svs

Source
------
The Cancer Genome Atlas Pancreatic Adenocarcinoma (TCGA-PAAD)
Downloaded from GDC (Genomic Data Commons) Data Portal
  https://portal.gdc.cancer.gov/
  https://api.gdc.cancer.gov/data/ac8a196a-0cfb-463b-bc31-f6356de2078d

GDC File ID  : ac8a196a-0cfb-463b-bc31-f6356de2078d
Case ID      : TCGA-HZ-7926
Sample type  : Primary Tumor (01Z)
Stain        : H&E (Hematoxylin and Eosin)
Slide type   : Diagnostic Slide
Data format  : SVS (Aperio ScanScope Virtual Slide)
File size    : 25,776,223 bytes (~24.6 MB)

Access
------
Open access -- no authentication required.
License: NIH GDC Data Use Agreement
  https://gdc.cancer.gov/access-data/data-access-processes-and-tools

Downloaded
----------
Date : 2026-05-01
Tool : GDC REST API (curl)

Purpose
-------
Test input for the LangGraphPrj_V5 pipeline
  https://github.com/bayjuan5/LangGraphPrj_V5
Used to verify that Node 1 (adaptive tiling), Node 2.1 (spatial feature
extraction), Node 2.2 (ROSIE biomarker inference), Node 3 (temporal
dynamics), and Node 4 (niche construction) run end-to-end on a publicly
available pancreatic cancer H&E whole-slide image.

How to open
-----------
  QuPath       : File > Open
  Python       : import openslide; slide = openslide.OpenSlide("*.svs")
  MATLAB       : bfopen('*.svs')  [requires Bio-Formats toolbox]
