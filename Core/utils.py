#!/usr/bin/env python3

import json

def convert_sets_to_lists(data):
	"""Recursively convert sets to lists in a dictionary."""
	if isinstance(data, dict):
		return {k: convert_sets_to_lists(v) for k, v in data.items()}
	elif isinstance(data, list):
		return [convert_sets_to_lists(v) for v in data]
	elif isinstance(data, set):
		return list(data)
	return data