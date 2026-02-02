#!/bin/bash
ls | egrep '^[a-f0-9]+-.*' | xargs rm -rf