from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import math
import os
import random
import sys
import time
import re

import csv
import numpy as np
random.seed(0)
np.random.seed(0)

from Bio import SeqIO
from Bio.SeqIO import FastaIO

import deepnovo_config






# write multi-line fasta file into single-line format
def write_fasta_1line(input_fasta_file, output_fasta_file):
  with open(input_fasta_file, "r")  as handle:
    record_list = list(SeqIO.parse(handle, "fasta"))
    print(input_fasta_file)
    print("Number of protein sequences: ", len(record_list))
  with open(output_fasta_file, "w") as handle:
    fasta_writer = FastaIO.FastaWriter(handle, wrap=None)
    fasta_writer.write_file(record_list)

# ~ input_fasta_file = "data/uniprot.human_all_isoforms.fasta"
# ~ output_fasta_file = input_fasta_file + ".1line"
# ~ write_fasta_1line(input_fasta_file, output_fasta_file)


# calculate peptide mass = N-terminus + amino acids + C-terminus
def compute_peptide_mass(peptide):
  """TODO(nh2tran): docstring.
  """

  #~ print("".join(["="] * 80)) # section-separating line ===
  #~ print("WorkerDB: _compute_peptide_mass()")

  peptide_mass = (deepnovo_config.mass_N_terminus
                  + sum(deepnovo_config.mass_AA[aa] for aa in peptide)
                  + deepnovo_config.mass_C_terminus)

  return peptide_mass

# ~ peptide = 'AAAAAAALQAK'
# ~ print(peptide)
# ~ print(compute_peptide_mass(peptide))


# calculate ppm of precursor_mz against peptide_mz
def check_mass_shift(input_feature_file):
  print("check_mass_shift()")

  print("input_feature_file = ", os.path.join(input_feature_file))

  with open(input_feature_file, mode="r") as input_handle:
    # header line
    line = input_handle.readline()
    # first feature
    line = input_handle.readline()
    precursor_ppm_list = []
    # ~ test_handle = open("test.txt", mode="w")
    while line:
      line_split = re.split(',|\r|\n', line)

      # parse raw peptide sequence
      raw_sequence = line_split[deepnovo_config.col_raw_sequence]
      raw_sequence_len = len(raw_sequence)
      peptide = []
      index = 0
      while index < raw_sequence_len:
        if raw_sequence[index] == "(":
          if peptide[-1] == "C" and raw_sequence[index:index + 8] == "(+57.02)":
            peptide[-1] = "C(Carbamidomethylation)"
            index += 8
          elif peptide[-1] == 'M' and raw_sequence[index:index + 8] == "(+15.99)":
            peptide[-1] = 'M(Oxidation)'
            index += 8
          elif peptide[-1] == 'N' and raw_sequence[index:index + 6] == "(+.98)":
            peptide[-1] = 'N(Deamidation)'
            index += 6
          elif peptide[-1] == 'Q' and raw_sequence[index:index + 6] == "(+.98)":
            peptide[-1] = 'Q(Deamidation)'
            index += 6
          else:  # unknown modification
            print("ERROR: unknown modification!")
            print("raw_sequence = ", raw_sequence)
            sys.exit()
        else:
          peptide.append(raw_sequence[index])
          index += 1

      precursor_mz = float(line_split[deepnovo_config.col_precursor_mz])
      precursor_charge = float(line_split[deepnovo_config.col_precursor_charge])
      peptide_mass = compute_peptide_mass(peptide)
      peptide_mz = (peptide_mass + precursor_charge * deepnovo_config.mass_H) / precursor_charge
      precursor_ppm = (precursor_mz - peptide_mz) / peptide_mz * 1e6
      # ~ print('precursor_mz = ', precursor_mz)
      # ~ print('peptide_mz = ', peptide_mz)
      # ~ print('precursor_ppm = ', precursor_ppm)
      # ~ print(abc)
      # ~ test_row = '\t'.join(['{0:.6f}'.format(x) for x in [peptide_mz, precursor_mz, precursor_ppm]])
      # ~ print(test_row, file=test_handle, end="\n")
      precursor_ppm_list.append(precursor_ppm)
      line = input_handle.readline()
    # ~ test_handle.close()
    print(np.mean(precursor_ppm_list))

# ~ input_feature_file = "identified_features_corrected.csv"
# ~ check_mass_shift(input_feature_file)


# randomly split a feature file into train/valid/test files for training
def split_feature_training(input_feature_file, proportion):
  print("split_feature_training()")

  print("input_feature_file = ", input_feature_file)
  print("proportion = ", proportion)

  output_file_train = input_feature_file + ".train"
  output_file_valid = input_feature_file + ".valid"
  output_file_test = input_feature_file + ".test"
  print("output_file_train =", output_file_train)
  print("output_file_valid =", output_file_valid)
  print("output_file_test =", output_file_test)


  num_total = 0
  num_train = 0
  num_valid = 0
  num_test = 0

  # read and write header line
  csv_reader = csv.DictReader(open(input_feature_file))
  csv_writer_train = csv.DictWriter(open(output_file_train, mode='w'), csv_reader.fieldnames)
  csv_writer_valid = csv.DictWriter(open(output_file_valid, mode='w'), csv_reader.fieldnames)
  csv_writer_test = csv.DictWriter(open(output_file_test, mode='w'), csv_reader.fieldnames)
  csv_writer_train.writeheader()
  csv_writer_valid.writeheader()
  csv_writer_test.writeheader()

  # iterate over feature rows
  # use random numbers 0/1/2 to assign rows to writers train/valid/test
  for row in csv_reader:
    num_total += 1
    random_num = np.random.choice(a=3, size=1, p=proportion)
    if random_num == 0:
      csv_writer = csv_writer_train
      num_train += 1
    elif random_num == 1:
      csv_writer = csv_writer_valid
      num_valid += 1
    else:
      csv_writer = csv_writer_test
      num_test += 1
    csv_writer.writerow(row)

  print("num_total =", num_total)
  print("num_train =", num_train)
  print("num_valid =", num_valid)
  print("num_test =", num_test)

# ~ input_feature_file = "data.training/aa.hla.bassani.nature_2016.mel_15/feature.csv.labeled"
# ~ proportion = [0.90, 0.05, 0.05]
# ~ split_feature_training(input_feature_file, proportion)


# randomly split a feature file into train/valid/test files for training
# train/valid/test do NOT SHARE PEPTIDES
def split_feature_training_noshare(input_feature_file, proportion):
  print("split_feature_training_noshare()")

  print("input_feature_file = ", input_feature_file)
  print("proportion = ", proportion)

  output_file_train = input_feature_file + ".train" + ".noshare"
  output_file_valid = input_feature_file + ".valid" + ".noshare"
  output_file_test = input_feature_file + ".test" + ".noshare"
  print("output_file_train =", output_file_train)
  print("output_file_valid =", output_file_valid)
  print("output_file_test =", output_file_test)

  num_total = 0
  num_unique = 0
  num_train = 0
  num_valid = 0
  num_test = 0

  peptide_train_list = []
  peptide_valid_list = []
  peptide_test_list = []

  # read and write header line
  csv_reader = csv.DictReader(open(input_feature_file))
  csv_writer_train = csv.DictWriter(open(output_file_train, mode='w'), csv_reader.fieldnames)
  csv_writer_valid = csv.DictWriter(open(output_file_valid, mode='w'), csv_reader.fieldnames)
  csv_writer_test = csv.DictWriter(open(output_file_test, mode='w'), csv_reader.fieldnames)
  csv_writer_train.writeheader()
  csv_writer_valid.writeheader()
  csv_writer_test.writeheader()

  # iterate over feature rows
  # if the peptide already exists, use the corresponding writer
  # if not, use random numbers 0/1/2 to assign writers train/valid/test
  for row in csv_reader:
    num_total += 1
    peptide = row['seq']
    if (peptide in peptide_train_list):
      csv_writer = csv_writer_train
      num_train += 1
    elif (peptide in peptide_valid_list):
      csv_writer = csv_writer_valid
      num_valid += 1
    elif (peptide in peptide_test_list):
      csv_writer = csv_writer_test
      num_test += 1
    else:
      num_unique += 1
      random_num = np.random.choice(a=3, size=1, p=proportion)
      if random_num == 0:
        peptide_train_list.append(peptide)
        csv_writer = csv_writer_train
        num_train += 1
      elif random_num == 1:
        peptide_valid_list.append(peptide)
        csv_writer = csv_writer_valid
        num_valid += 1
      else:
        peptide_test_list.append(peptide)
        csv_writer = csv_writer_test
        num_test += 1
    csv_writer.writerow(row)

  print("num_total =", num_total)
  print("num_unique =", num_unique)
  print("num_train =", num_train)
  print("num_valid =", num_valid)
  print("num_test =", num_test)

# ~ input_feature_file = "data.training/aa.hla.bassani.nature_2016.mel_15/feature.csv.labeled"
# ~ proportion = [0.90, 0.05, 0.05]
# ~ split_feature_training_noshare(input_feature_file, proportion)


# split a feature file into labeled and unlabeled files
def split_feature_unlabel(input_feature_file):
  """TODO(nh2tran): docstring."""

  print(''.join(['='] * 80)) # section-separating line
  print("split_feature_unlabel()")
  print("input_feature_file =", input_feature_file)

  output_file_labeled = input_feature_file + ".labeled"
  output_file_unlabeled = input_feature_file + ".unlabeled"
  print("output_file_labeled =", output_file_labeled)
  print("output_file_unlabeled =", output_file_unlabeled)

  num_labeled = 0
  num_unlabeled = 0

  # read and write header line
  csv_reader = csv.DictReader(open(input_feature_file))
  csv_writer_labeled = csv.DictWriter(open(output_file_labeled, mode='w'), csv_reader.fieldnames)
  csv_writer_unlabeled = csv.DictWriter(open(output_file_unlabeled, mode='w'), csv_reader.fieldnames)
  csv_writer_labeled.writeheader()
  csv_writer_unlabeled.writeheader()

  # iterate over feature rows
  # unlabeled features have empty peptide sequence
  for row in csv_reader:
    peptide = row['seq']
    if peptide == '':
      csv_writer = csv_writer_unlabeled
      num_unlabeled += 1
    else:
      csv_writer = csv_writer_labeled
      num_labeled += 1
    csv_writer.writerow(row)

  print("num_labeled =", num_labeled)
  print("num_unlabeled =", num_unlabeled)

# ~ input_feature_file = "data.training/aa.hla.bassani.nature_2016.mel_15/feature.csv"
# ~ split_feature_unlabel(input_feature_file)


# merge multiple mgf files into one, adding fraction ID to scan ID
def merge_mgf_file(input_file_list, fraction_list, output_file):
  print("cat_file_mgf()")
  
  # iterate over mgf files and their lines
  counter = 0
  with open(output_file, mode="w") as output_handle:
    for input_file, fraction in zip(input_file_list, fraction_list):
      print("input_file = ", os.path.join(input_file))
      with open(input_file, mode="r") as input_handle:
        for line in input_handle.readlines():
          if "SCANS=" in line: # a spectrum found
            counter += 1
            scan = re.split('=|\n|\r', line)[1]
            # re-number scan id
            output_handle.write("SCANS=F{0}:{1}\n".format(fraction, scan))
          else:
            output_handle.write(line)
  print("output_file = {0:s}".format(output_file))
  print("counter = {0:d}".format(counter))


# merge multiple feature files into one, adding fraction ID to feature & scan ID
def merge_feature_file(input_file_list, fraction_list, output_file):
  print("merge_feature_file()")
  
  # read and write header line
  csv_reader = csv.DictReader(open(input_file_list[0]))
  csv_writer = csv.DictWriter(open(output_file, mode='w'), csv_reader.fieldnames)
  csv_writer.writeheader()

  # iterate over feature files and their rows
  counter = 0
  for input_file, fraction in zip(input_file_list, fraction_list):
    print("input_file = ", os.path.join(input_file))
    csv_reader = csv.DictReader(open(input_file))
    for row in csv_reader:
      counter += 1
      # add fraction to feature id
      feature_id = row['spec_group_id']
      feature_id = "F" + str(fraction) + ":" + feature_id
      row['spec_group_id'] = feature_id
      # add fraction to scan id
      scan_list = re.split(';', row['scans'])
      scan_list = ["F" + str(fraction) + ":" + x for x in scan_list]
      row['scans'] = ";".join(scan_list)
      # join the line back together and write to output
      csv_writer.writerow(row)
  print("output_file = {0:s}".format(output_file))
  print("counter = {0:d}".format(counter))

# ~ folder_path = "data.training/aa.hla.bassani.nature_2016.mel_15/"
# ~ fraction_list = range(0, 15+1)
# ~ merge_mgf_file(
    # ~ input_file_list=[folder_path + "export_" + str(i) + ".mgf" for i in fraction_list],
    # ~ fraction_list=fraction_list,
    # ~ output_file=folder_path + "spectrum.mgf")
# ~ merge_feature_file(
    # ~ input_file_list=[folder_path + "export_" + str(i) + ".csv" for i in fraction_list],
    # ~ fraction_list=fraction_list,
    # ~ output_file=folder_path + "feature.csv")
