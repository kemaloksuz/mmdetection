import mmcv

from mmdet.core import bbox_mapping, tensor2imgs
from .. import builder
from ..registry import DETECTORS
from .base import BaseDetector
from .test_mixins import RPNTestMixin


@DETECTORS.register_module
class RPN(BaseDetector, RPNTestMixin):

    def __init__(self,
                 backbone,
                 neck,
                 rpn_head,
                 train_cfg,
                 test_cfg,
                 pretrained=None):
        super(RPN, self).__init__()
        self.backbone = builder.build_backbone(backbone)
        self.neck = builder.build_neck(neck) if neck is not None else None
        self.rpn_head = builder.build_head(rpn_head)
        self.train_cfg = train_cfg
        self.test_cfg = test_cfg
        self.init_weights(pretrained=pretrained)

    def init_weights(self, pretrained=None):
        super(RPN, self).init_weights(pretrained)
        self.backbone.init_weights(pretrained=pretrained)
        if self.with_neck:
            self.neck.init_weights()
        self.rpn_head.init_weights()

    def extract_feat(self, img):
        x = self.backbone(img)
        if self.with_neck:
            x = self.neck(x)
        return x

    def forward_dummy(self, img):
        x = self.extract_feat(img)
        rpn_outs = self.rpn_head(x)
        return rpn_outs

    def forward_train(self,
                      img,
                      img_metas,
                      gt_bboxes=None,
                      gt_bboxes_ignore=None,
                      gt_masks=None):
        if self.train_cfg.rpn.get('debug', False):
            self.rpn_head.debug_imgs = tensor2imgs(img)

        x = self.extract_feat(img)
        rpn_outs = self.rpn_head(x)

        rpn_loss_inputs = rpn_outs + (gt_bboxes, img_metas, self.train_cfg.rpn)
        losses = self.rpn_head.loss(
            *rpn_loss_inputs, gt_bboxes_ignore=gt_bboxes_ignore, gt_masks=gt_masks)
        return losses

    def simple_test(self, img, img_metas, rescale=False):
        x = self.extract_feat(img)
        proposal_list = self.simple_test_rpn(x, img_metas, self.test_cfg.rpn)
        if rescale:
            for proposals, meta in zip(proposal_list, img_metas):
                proposals[:, :4] /= meta['scale_factor']
        # TODO: remove this restriction
        return proposal_list[0].cpu().numpy()

    def aug_test(self, imgs, img_metas, rescale=False):
        proposal_list = self.aug_test_rpn(
            self.extract_feats(imgs), img_metas, self.test_cfg.rpn)
        if not rescale:
            for proposals, img_meta in zip(proposal_list, img_metas[0]):
                img_shape = img_meta['img_shape']
                scale_factor = img_meta['scale_factor']
                flip = img_meta['flip']
                proposals[:, :4] = bbox_mapping(proposals[:, :4], img_shape,
                                                scale_factor, flip)
        # TODO: remove this restriction
        return proposal_list[0].cpu().numpy()

    def show_result(self, data, result, dataset=None, top_k=20):
        """Show RPN proposals on the image.

        Although we assume batch size is 1, this method supports arbitrary
        batch size.
        """
        img_tensor = data['img'][0]
        img_metas = data['img_metas'][0].data[0]
        imgs = tensor2imgs(img_tensor, **img_metas[0]['img_norm_cfg'])
        assert len(imgs) == len(img_metas)
        for img, img_meta in zip(imgs, img_metas):
            h, w, _ = img_meta['img_shape']
            img_show = img[:h, :w, :]
            mmcv.imshow_bboxes(img_show, result, top_k=top_k)
