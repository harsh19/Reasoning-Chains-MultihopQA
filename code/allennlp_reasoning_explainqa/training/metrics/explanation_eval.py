from overrides import overrides
import numpy as np
from allennlp.training.metrics.metric import Metric
from allennlp_reasoning_explainqa.common.constants import *
from collections import Counter
import random


def dcg_score(y_true, y_score, k=10, gains="exponential"):
    """Discounted cumulative gain (DCG) at rank k
    Parameters
    ----------
    y_true : array-like, shape = [n_samples]
        Ground truth (true relevance labels).
    y_score : array-like, shape = [n_samples]
        Predicted scores.
    k : int
        Rank.
    gains : str
        Whether gains should be "exponential" (default) or "linear".
    Returns
    -------
    DCG @k : float
    """
    order = np.argsort(y_score)[::-1]
    y_true = np.take(y_true, order[:k])
    if gains == "exponential":
        gains = 2 ** y_true - 1
    elif gains == "linear":
        gains = y_true
    else:
        raise ValueError("Invalid gains option.")
    # highest rank is 1 so +2 instead of +1
    discounts = np.log2(np.arange(len(y_true)) + 2)
    # print("gains,discounts = ", gains,discounts)
    return np.sum(gains / discounts)


def ndcg_score(y_true, y_score, k=10, gains="exponential"):
    """Normalized discounted cumulative gain (NDCG) at rank k
    Parameters
    ----------
    y_true : array-like, shape = [n_samples]
        Ground truth (true relevance labels).
    y_score : array-like, shape = [n_samples]
        Predicted scores.
    k : int
        Rank.
    gains : str
        Whether gains should be "exponential" (default) or "linear".
    Returns
    -------
    NDCG @k : float
    """
    best = dcg_score(y_true, y_true, k, gains)
    actual = dcg_score(y_true, y_score, k, gains)
    return actual / best




@Metric.register("explanation_eval")
class ExplanationEval(Metric):

    def __init__(self, pos_label=1, neg_label=0) -> None:
        self._predictions = {}
        # self._gt = {}
        self._id_count = 0
        self._pos_label = pos_label
        self._neg_label = neg_label
        self._labels = [pos_label,neg_label]

    @overrides
    def __call__(self, ques_id, choice_type, ground_truth_label, score):
        """
        Parameters
        ----------
        value : ``float``
            The value to average.
        """
        # print("[] __call__")
        if choice_type in CORRECT_OPTION_TAG_LIST:
            assert ground_truth_label in self._labels, "Label not known"
            if ques_id not in self._predictions:
                self._predictions[ ques_id ] = []
                self._id_count += 1
            self._predictions[ques_id].append({'score':score, 'ground_truth':ground_truth_label})
            # self._gt[ques_id].append(ground_truth)

    @overrides
    def get_metric(self, reset: bool = False):
        if reset:
            print("explain_eval: Counter(len(vals)) : ", Counter( [ len(val) for val in self._predictions.values() ] ))
        ret = {"explainP1":[],"explainP1_normalized":[], "explainP2":[], "explainP5":[], "explainNDCG":[]}
        total_label_counts = {'label_'+str(k):0 for k in self._labels}
        for id,vals in self._predictions.items():
            # print(" ======= explain_eval : id = ", id)
            random.shuffle(vals) #hack to avoid high scores in case of ties and correct ones got in first
            vals = sorted(vals, key=lambda x:-x['score']) # sort by decreasing order of score
            cnt_pos_flag = 0
            # cnt_pos = 0
            y_true = [val['ground_truth'] for val in vals]
            y_score = [val['score'] for val in vals]
            total_true = sum(y_true)
            if total_true>0:
                # ndcg_exp = ndcg_score(y_true, y_score, k=10, gains="exponential")
                ndcg = ndcg_score(y_true, y_score, k=10, gains="linear")
            else:
                ndcg_exp = ndcg = 0
            # print("id=",id,"y_true, y_score, ndcg = ", y_true, y_score, ndcg)
            # ret['explainNDCG_exp'].append(ndcg_exp)
            ret['explainNDCG'].append(ndcg)

            ndcg_numerator = 0.0
            ndcg_denominator = 0.0
            discount = 1.0
            discount_den = 1.0
            for j,val in enumerate(vals): # to do what if num items is less than 5 ? -- will effect R@5
                # print("explain_eval : j = ", j, " | val = ", val)
                if val['ground_truth'] == self._pos_label:
                    cnt_pos_flag = 1   # since just want to know ehteher it is there or not
                    ndcg_numerator += (discount*1.0)
                    # denominator represents maximum possible. whenever encounter a positive, denominator value should increase
                    # since it is 0/1, it simple here. no need to sort.
                    # cnt_pos += 1
                    ndcg_denominator += (discount_den * 1.0)
                    discount_den *= 0.5
                    # total_label_counts[self._pos_label] += 1
                    labelk = self._pos_label
                else:
                    labelk = self._neg_label
                total_label_counts['label_'+str(labelk)] += 1
                if j == 0:
                    ret['explainP1'].append(cnt_pos_flag)
                if j == 1:
                    ret[ 'explainP2' ].append(cnt_pos_flag)
                if j == 4:
                    ret[ 'explainP5' ].append(cnt_pos_flag)
                discount *= 0.5
            if cnt_pos_flag>0:
                ret['explainP1_normalized'].append(ret['explainP1'][-1])
            assert ndcg_numerator <= ndcg_denominator # sanity check
            if ndcg_denominator <=0:
                ndcg = 0.0
            else:
                ndcg = ndcg_numerator/ndcg_denominator
        self.ret = {k:{'items':len(lst),'score':np.mean(lst)} for k,lst in ret.items()}
        return_metric = {}
        for k, lst in ret.items():
            return_metric[ k + '_items' ] = len(lst)
            if len(lst) > 0:
                return_metric[k] = np.mean(lst)
        return_metric.update(total_label_counts)
        # print(" === return_metric = ", return_metric)
        if reset:
            self.reset()
        return return_metric

    @overrides
    def reset(self):
        self._predictions = {}
        # self._gt = {}
        self._id_count = 0
        self.ret = {}

    def __str__(self):
        return str(self.ret)  # f"CocovalsMeasures(em={self._total_em}, f1={self._total_f1})"





import copy
@Metric.register("precision_eval")
class PrecisionEval(Metric):

    def __init__(self, use_aggregate_scoring:bool = True) -> None:
        self._predictions = {}
        self._id_option_to_type = {}
        # self._gt = {}
        self._id_count = 0
        self.ret = {}
        self._use_aggregate_scoring = use_aggregate_scoring

    @overrides
    def __call__(self, ques_id, choice_type, ground_truth_label, score, option=None):
        assert choice_type in ALL_OPTION_TAG_LIST, "choice_type " + str(choice_type) + " not undertstood"
        if ques_id not in self._predictions:
            self._predictions[ ques_id ] = []
            self._id_count += 1
        self._predictions[ques_id].append({'score':score, 'choice_type':choice_type, 'option':option})
        # self._gt[ques_id].append(ground_truth)

    def _get_aggregate_score(self, sorted_lst, max_k=5):
        discount = 1.0
        ret = 0.0
        den = 0.0
        for k,val in enumerate(sorted_lst):
            if k>=max_k:
                break
            ret += (val['score']*discount)
            den += discount
            discount *= 0.5
        return ret/den

    def _group_by_choice(self):
        ret = {}
        chains_per_id = {}
        for k, vals in self._predictions.items():
            chains_per_id[id] = len(vals)
            tmp = {}
            ret[k] = []
            for val in vals:
                option = val['option']
                if option not in tmp:
                    tmp[option] = []
                tmp[option].append(val)
            # ret[k] = copy.deepcopy( vals[0] )
            for option in tmp:
                tmp[ option ] = sorted(tmp[option], key=lambda x:-x['score'])
                ret[k].append( copy.deepcopy(tmp[option][0]) )
                if self._use_aggregate_scoring:
                    ret[k][-1].update( {'score':self._get_aggreagte_score(tmp[option])})
        print( 'chains_per_id', Counter(chains_per_id.values()) )
        return ret

    @overrides
    def get_metric(self, reset: bool = False, eval_with_aggregation:bool = False):
        ret = {"QA_R1":[], "QA_R2":[], "QA_R5":[]}
        predictions_to_use = self._predictions
        if eval_with_aggregation:
            predictions_to_use = self._group_by_choice()
        for id,vals in predictions_to_use.items():
            # keep a track
            vals = sorted(vals, key=lambda x:-x['score']) # sort by decreasing order of score
            cnt_pos = 0
            for j,val in enumerate(vals): # to do what if num items is less than 5 ? -- will effect R@5
                if val['choice_type'] in CORRECT_OPTION_TAG_LIST:
                    cnt_pos = 1   # since just want to know ehteher it is there or not
                if j == 0:
                    ret['QA_R1'].append(cnt_pos)
                elif j == 1:
                    ret[ 'QA_R2' ].append(cnt_pos)
                elif j == 4:
                    ret[ 'QA_R5' ].append(cnt_pos)
            # if cnt_pos is not 0, then print/add to list
        self.ret = {k: {'items': len(lst), 'score': np.mean(lst) } for k, lst in ret.items() }
        return_metric = {}
        for k, lst in ret.items():
            return_metric[ k + '_items' ] = len(lst)
            if len(lst) > 0:
                return_metric[ k ] = np.mean(lst)
        # print(" === return_metric = ", return_metric)
        if reset:
            self.reset()
        return return_metric

    @overrides
    def reset(self):
        self._predictions = {}
        # self._gt = {}
        self._id_count = 0

    def __str__(self):
        return str(self.ret)  # f"CocovalsMeasures(em={self._total_em}, f1={self._total_f1})"



if __name__ == '__main__':
    explain_eval = ExplanationEval()

    dummy1 = [
        [1, 1, 1.5],
        [1, 1, 1.0],
        [1, 0, 0.9] # perfect ranking
    ]
    for ques_id,ground_truth_label,score in dummy1:
        explain_eval(ques_id, CORRECT_OPTION_TAG, ground_truth_label, score)
    print(explain_eval.get_metric(reset=True))
    print("============")
    # {'explainP1_items': 1, 'explainP1': 1.0, 'explainP1_normalized_items': 1, 'explainP1_normalized': 1.0,
    #  'explainP2_items': 1, 'explainP2': 1.0, 'explainP5_items': 0, 'explainNDCG_items': 1, 'explainNDCG': 1.0,
    #  'explainNDCG_exp_items': 1, 'explainNDCG_exp': 1.0, 'label_1': 2, 'label_0': 1}

    dummy1 = [
        [1, 1, 1.5],
        [1, 1, 1.0],
        [1, 0, 0.9], # perfect ranking
        [2, 0, 1.5],
        [2, 0, 1.0],
        [2, 1, 0.9]  # completely opposite ranking
    ]
    for ques_id,ground_truth_label,score in dummy1:
        explain_eval(ques_id, CORRECT_OPTION_TAG, ground_truth_label, score)
    print(explain_eval.get_metric(reset=True))
    print("============")

    dummy1 = [
        [1, 0, 1.0],
        [1, 1, 1.0],
        [1, 1, 1.0]
    ]
    for ques_id, ground_truth_label, score in dummy1:
        explain_eval(ques_id, CORRECT_OPTION_TAG, ground_truth_label, score)
    print(explain_eval.get_metric(reset=True))
    print("============")

    dummy1 = [
        [1, 1, 1.0],
        [1, 1, 1.0],
        [1, 0, 1.0]
    ]
    for ques_id, ground_truth_label, score in dummy1:
        explain_eval(ques_id, CORRECT_OPTION_TAG, ground_truth_label, score)
    print(explain_eval.get_metric(reset=True))
    print("============")


    dummy1 = [
        [1, 0, 1.0],
        [1, 1, 1.01],
        [1, 1, 1.01]
    ]
    for ques_id, ground_truth_label, score in dummy1:
        explain_eval(ques_id, CORRECT_OPTION_TAG, ground_truth_label, score)
    print(explain_eval.get_metric(reset=True))
    print("============")

    dummy1 = [
        [1, 0, 1.02],
        [1, 1, 1.01],
        [1, 1, 1.01]
    ]
    for ques_id, ground_truth_label, score in dummy1:
        explain_eval(ques_id, CORRECT_OPTION_TAG, ground_truth_label, score)
    print(explain_eval.get_metric(reset=True))
    print("============")

    dummy1 = [
        [1, 0, 1.0],
        [1, 0, 1.0],
        [1, 1, 1.0]
    ]
    for ques_id, ground_truth_label, score in dummy1:
        explain_eval(ques_id, CORRECT_OPTION_TAG, ground_truth_label, score)
    print(explain_eval.get_metric(reset=True))
    print("============")

    dummy1 = [
        [1, 0, 1.0],
        [1, 0, 1.0],
        [1, 0, 1.0]
    ]
    for ques_id, ground_truth_label, score in dummy1:
        explain_eval(ques_id, CORRECT_OPTION_TAG, ground_truth_label, score)
    print(explain_eval.get_metric(reset=True))
    print("============")

    dummy1 = [
        [1, 1, 1.0],
        [1, 1, 1.0],
    ]
    for ques_id, ground_truth_label, score in dummy1:
        explain_eval(ques_id, CORRECT_OPTION_TAG, ground_truth_label, score)
    print(explain_eval.get_metric(reset=True))

    #  env PYTHONPATH=. python allennlp_reasoning_explainqa/training/metrics/explanation_eval.py