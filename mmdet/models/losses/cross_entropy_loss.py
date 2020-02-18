import torch
import torch.nn as nn
import torch.nn.functional as F
import numpy as np

from ..registry import LOSSES
from pathlib import Path
from .utils import weight_reduce_loss
import pdb

def get_valid_labels(valid_labels,
                     valid_preds,
                     loss
                     ):
    #pdb.set_trace()
    tuple_ = np.concatenate((np.expand_dims(valid_preds.detach().cpu().numpy(), 1), \
                             np.expand_dims(valid_labels.detach().cpu().numpy(), 1), \
                             np.expand_dims(loss.detach().cpu().numpy(), 1)), \
                             axis = 1)
    p = Path("/home/cancam/imgworkspace/mmdetection/class_analysis_ce.txt")
    with p.open("ab") as fp:
        np.savetxt(fp, tuple_)
        fp.close()

def cross_entropy(pred, label, weight=None, reduction='mean', avg_factor=None):
    # element-wise losses)
    # label'da valid labellar mı geliyor?
    loss = F.cross_entropy(pred, label, reduction='none')
    pred_softmax = F.softmax(pred)
    valid_inds = ((weight>0).nonzero()).flatten()
    pred_labels = pred_softmax[valid_inds, :].argmax(dim=1)
    #get_valid_labels(label[valid_inds], pred_labels, loss)
    # check variables and send them to get_valid_labels.
    # apply weights and do the reduction
    if weight is not None:
        weight = weight.float()
    loss = weight_reduce_loss(
        loss, weight=weight, reduction=reduction, avg_factor=avg_factor)

    return loss


def _expand_binary_labels(labels, label_weights, label_channels):
    bin_labels = labels.new_full((labels.size(0), label_channels), 0)
    inds = torch.nonzero(labels >= 1).squeeze()
    if inds.numel() > 0:
        bin_labels[inds, labels[inds] - 1] = 1
    if label_weights is None:
        bin_label_weights = None
    else:
        bin_label_weights = label_weights.view(-1, 1).expand(
            label_weights.size(0), label_channels)
    return bin_labels, bin_label_weights


def binary_cross_entropy(pred,
                         label,
                         weight=None,
                         reduction='mean',
                         avg_factor=None):
    if pred.dim() != label.dim():
        label, weight = _expand_binary_labels(label, weight, pred.size(-1))

    # weighted element-wise losses
    if weight is not None:
        weight = weight.float()
    loss = F.binary_cross_entropy_with_logits(
        pred, label.float(), weight, reduction='none')
    # do the reduction for the weighted loss
    loss = weight_reduce_loss(loss, reduction=reduction, avg_factor=avg_factor)

    return loss


def mask_cross_entropy(pred, target, label, reduction='mean', avg_factor=None):
    # TODO: handle these two reserved arguments
    assert reduction == 'mean' and avg_factor is None
    num_rois = pred.size()[0]
    inds = torch.arange(0, num_rois, dtype=torch.long, device=pred.device)
    pred_slice = pred[inds, label].squeeze(1)
    return F.binary_cross_entropy_with_logits(
        pred_slice, target, reduction='mean')[None]


@LOSSES.register_module
class CrossEntropyLoss(nn.Module):

    def __init__(self,
                 use_sigmoid=False,
                 use_mask=False,
                 reduction='mean',
                 loss_weight=1.0):
        super(CrossEntropyLoss, self).__init__()
        assert (use_sigmoid is False) or (use_mask is False)
        self.use_sigmoid = use_sigmoid
        self.use_mask = use_mask
        self.reduction = reduction
        self.loss_weight = loss_weight

        if self.use_sigmoid:
            self.cls_criterion = binary_cross_entropy
        elif self.use_mask:
            self.cls_criterion = mask_cross_entropy
        else:
            self.cls_criterion = cross_entropy

    def forward(self,
                cls_score,
                label,
                weight=None,
                avg_factor=None,
                reduction_override=None,
                **kwargs):
        assert reduction_override in (None, 'none', 'mean', 'sum')
        reduction = (
            reduction_override if reduction_override else self.reduction)
        loss_cls = self.loss_weight * self.cls_criterion(
            cls_score,
            label,
            weight,
            reduction=reduction,
            avg_factor=avg_factor,
            **kwargs)
        return loss_cls
