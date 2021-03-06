#!/usr/bin/env bash


MODEL_NAME=normal

CUDA_VISIBLE_DEVICES=1 python -m allennlp.run train configs/normalfinal.json --serialization-dir tmp/"$MODEL_NAME"/ --include-package allennlp_reasoning_explainqa  --overrides '{ "dataset_reader": { "debug": false } }'

#### e-QASC
CUDA_VISIBLE_DEVICES=1 python -m allennlp.run evaluate --output-file predictions/"$MODEL_NAME".dev.eval --weights-file tmp/"$MODEL_NAME"/best.th --include-package allennlp_reasoning_explainqa  --overrides '{ "dataset_reader": { "force_add_gold_chain_val": false, "debug": false, "negative_sampling_rate_val": 1.0} }' --cuda-device 0 tmp/"$MODEL_NAME"/model.tar.gz ../data/eqasc/eqasc_dev_grc.json
cat predictions/"$MODEL_NAME".dev.eval

CUDA_VISIBLE_DEVICES=1 python -m allennlp.run evaluate --output-file predictions/"$MODEL_NAME".test.eval --weights-file tmp/"$MODEL_NAME"/best.th --include-package allennlp_reasoning_explainqa  --overrides '{ "dataset_reader": { "force_add_gold_chain_val": false, "debug": false, "negative_sampling_rate_val": 1.0} }' --cuda-device 0 tmp/"$MODEL_NAME"/model.tar.gz ../data/eqasc/eqasc_test_grc.json
cat predictions/"$MODEL_NAME".test.eval


# "threshold_max": 0.851398
CUDA_VISIBLE_DEVICES=1 python -m allennlp.run evaluate --output-file predictions/"$MODEL_NAME".test.giventhresh.eval --weights-file tmp/"$MODEL_NAME"/best.th --include-package allennlp_reasoning_explainqa  --overrides '{ "dataset_reader": { "force_add_gold_chain_val": false, "debug": false, "negative_sampling_rate_val": 1.0}, "model":{"f1_given_thresh":0.851398}  }' --cuda-device 0 tmp/"$MODEL_NAME"/model.tar.gz ../data/eqasc/eqasc_test_grc.json
cat predictions/"$MODEL_NAME".test.giventhresh.eval


#### e-QASC-perturbed
# mkdir predictions
CUDA_VISIBLE_DEVICES=1 python -m allennlp.run predict --output-file predictions/"$MODEL_NAME".new.test.replace.modified.predict --weights-file tmp/"$MODEL_NAME"/best.th --include-package allennlp_reasoning_explainqa  --overrides '{ "model":{"pred_thresh":0.851398}  }' --cuda-device 0 tmp/"$MODEL_NAME"/model.tar.gz ../data/eqasc_perturbed/turk_modified_test.tsv --predictor new_predictor_replace_newtest_mod
mv predictions/new_predictor_replace_new_mod.tsv predictions/"$MODEL_NAME".modified.tsv
CUDA_VISIBLE_DEVICES=1 python -m allennlp.run predict --output-file predictions/"$MODEL_NAME".new.test.replace.orig.predict --weights-file tmp/"$MODEL_NAME"/best.th --include-package allennlp_reasoning_explainqa  --overrides '{ "model":{"pred_thresh":0.851398}  }' --cuda-device 0 tmp/"$MODEL_NAME"/model.tar.gz ../data/eqasc_perturbed/turk_modified_test.tsv --predictor new_predictor_replace_newtest_orig
mv predictions/new_predictor_replace_new_orig.tsv predictions/"$MODEL_NAME".original.tsv
python allennlp_reasoning_explainqa/model/analyze_eqasc_perturbed.py  predictions/"$MODEL_NAME".original.tsv predictions/"$MODEL_NAME".modified.tsv > predictions/"$MODEL_NAME".eqasc_pertrubed.analysis
cat predictions/"$MODEL_NAME".eqasc_pertrubed.analysis


#### e-OBQA
CUDA_VISIBLE_DEVICES=1 python -m allennlp.run evaluate --output-file predictions/"$MODEL_NAME".obqa.test.eval --weights-file tmp/"$MODEL_NAME"/best.th --include-package allennlp_reasoning_explainqa  --overrides '{ "dataset_reader": { "force_add_gold_chain": false,"force_add_gold_chain_val": false, "debug": false, "data_version":"obqa", "skip_negative_choices":true }, "model":{"pred_thresh":0.851398} }' --cuda-device 0 tmp/"$MODEL_NAME"/model.tar.gz ../data/eobqa/obqa_chains.tsv.processed.tsv
cat predictions/"$MODEL_NAME".obqa.test.eval


