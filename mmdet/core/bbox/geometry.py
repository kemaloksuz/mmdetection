import torch
import numpy as np
import pdb
import matplotlib.pyplot as plt
from matplotlib import patches as patch
import random


def bbox_overlaps(bboxes1, bboxes2, mode='iou', is_aligned=False):
    """Calculate overlap between two set of bboxes.

    If ``is_aligned`` is ``False``, then calculate the ious between each bbox
    of bboxes1 and bboxes2, otherwise the ious between each aligned pair of
    bboxes1 and bboxes2.

    Args:
        bboxes1 (Tensor): shape (m, 4)
        bboxes2 (Tensor): shape (n, 4), if is_aligned is ``True``, then m and n
            must be equal.
        mode (str): "iou" (intersection over union) or iof (intersection over
            foreground).

    Returns:
        ious(Tensor): shape (m, n) if is_aligned == False else shape (m, 1)
    """

    assert mode in ['iou', 'iof']

    rows = bboxes1.size(0)
    cols = bboxes2.size(0)
    if is_aligned:
        assert rows == cols

    if rows * cols == 0:
        return bboxes1.new(rows, 1) if is_aligned else bboxes1.new(rows, cols)

    if is_aligned:
        lt = torch.max(bboxes1[:, :2], bboxes2[:, :2])  # [rows, 2]
        rb = torch.min(bboxes1[:, 2:], bboxes2[:, 2:])  # [rows, 2]

        wh = (rb - lt + 1).clamp(min=0)  # [rows, 2]
        overlap = wh[:, 0] * wh[:, 1]
        area1 = (bboxes1[:, 2] - bboxes1[:, 0] + 1) * (
            bboxes1[:, 3] - bboxes1[:, 1] + 1)
        if mode == 'iou':
            area2 = (bboxes2[:, 2] - bboxes2[:, 0] + 1) * (
                bboxes2[:, 3] - bboxes2[:, 1] + 1)
            ious = overlap / (area1 + area2 - overlap)
        else:
            ious = overlap / area1
    else:
        lt = torch.max(bboxes1[:, None, :2], bboxes2[:, :2])  # [rows, cols, 2]
        rb = torch.min(bboxes1[:, None, 2:], bboxes2[:, 2:])  # [rows, cols, 2]

        wh = (rb - lt + 1).clamp(min=0)  # [rows, cols, 2]
        overlap = wh[:, :, 0] * wh[:, :, 1]
        area1 = (bboxes1[:, 2] - bboxes1[:, 0] + 1) * (
            bboxes1[:, 3] - bboxes1[:, 1] + 1)

        if mode == 'iou':
            area2 = (bboxes2[:, 2] - bboxes2[:, 0] + 1) * (
                bboxes2[:, 3] - bboxes2[:, 1] + 1)
            ious = overlap / (area1[:, None] + area2 - overlap)
        else:
            ious = overlap / (area1[:, None])

    return ious

def integral_image_compute(masks,gt_number,h,w):
    integral_images= [None] * gt_number
    pad_row=torch.zeros([gt_number,1,w]).type(torch.cuda.ByteTensor)
    pad_col=torch.zeros([gt_number,h+1,1]).type(torch.cuda.ByteTensor)
    integral_images=torch.cumsum(torch.cumsum(torch.cat([pad_col,torch.cat([pad_row,masks],dim=1)], dim=2),dim=1), dim=2)
    return integral_images

def integral_image_fetch(mask,bboxes):
    #import pdb
    bboxes[:,[2,3]]+=1
    print(torch.min(bboxes[:,0]),torch.min(bboxes[:,1]),torch.max(bboxes[:,2]),torch.max(bboxes[:,3]))
    #Create indices
    TLx=bboxes[:,0].tolist()
    TLy=bboxes[:,1].tolist()
    BRx=bboxes[:,2].tolist()
    BRy=bboxes[:,3].tolist()
    area=mask[BRy,BRx]+mask[TLy,TLx]-mask[TLy,BRx]-mask[BRy,TLx]
    bboxes[:,[2,3]]-=1
    return area

def mask_plotter(mask_aware_ious, overlaps, gt_masks, gt_bboxes, bboxes, cond, fntsize=14):
    '''
    condition=[minSoftIoU, maxSoftIoU, minIoU, maxIoU]
    '''
    #bboxes=torch.clamp(bboxes, min=0)
    #bboxes[:,[0,2]]=torch.clamp(bboxes[:,[0,2]], max=image_w-1)
    #bboxes[:,[1,3]]=torch.clamp(bboxes[:,[1,3]], max=image_h-1)
    pdb.set_trace()
    valid_ind=(mask_aware_ious>cond[0]) & (mask_aware_ious<cond[1]) & (overlaps>cond[2]) & (overlaps<cond[3])
    nonzero_iou_ind=np.nonzero(valid_ind)
    valid_set_size=nonzero_iou_ind.shape[0]
    if valid_set_size==0:
        return
    no=random.randint(0,valid_set_size-1)
    pltgt,pltanc=nonzero_iou_ind[no]
    
    
    fig, ax = plt.subplots(1)
    ax.imshow(gt_masks[pltgt])
    tempRect=patch.Rectangle((bboxes[pltanc,0],bboxes[pltanc,1]), bboxes[pltanc,2]-bboxes[pltanc,0], bboxes[pltanc,3]-bboxes[pltanc,1],linewidth=3,edgecolor='r',facecolor='none')
    ax.add_patch(tempRect) 
    
    tempRect=patch.Rectangle((gt_bboxes[pltgt,0],gt_bboxes[pltgt,1]), gt_bboxes[pltgt,2]-gt_bboxes[pltgt,0], gt_bboxes[pltgt,3]-gt_bboxes[pltgt,1],linewidth=3,edgecolor='g',facecolor='none')
    ax.add_patch(tempRect)        

    ax.tick_params(labelsize=fntsize)      
    plt.xlabel('x', fontsize=fntsize)
    plt.ylabel('y', fontsize=fntsize)
    ax.text(0, 0, "IoU= "+np.array2string(overlaps[pltgt,pltanc].cpu().numpy())+", "+\
                "\n MaskIoU="+np.array2string(mask_aware_ious[pltgt,pltanc].cpu().numpy()), fontsize=fntsize)
    plt.show()

def segm_overlaps(gt_masks, gt_bboxes, bboxes, overlaps, min_overlap, harmonic_mean_weight=1, plot=0): 
    #import pdb

    #import time
    with torch.no_grad():
   # start = time.time()
        segm_ious=overlaps.data.new_zeros(overlaps.size())
        soft_ious=overlaps.data.new_zeros(overlaps.size())
        #Convert list to torch
        all_gt_masks=torch.from_numpy(gt_masks).type(torch.cuda.ByteTensor)
        gt_number,image_h,image_w=all_gt_masks.size()
        #pdb.set_trace()
        integral_images=integral_image_compute(all_gt_masks,gt_number,image_h,image_w).type(torch.cuda.FloatTensor) 
        #end1 = time.time()
        for i in range(gt_number):
            #larger_ind = overlaps[i,:] > (min_overlap / (2-min_overlap))
            larger_ind = overlaps[i,:] > (min_overlap / (2-min_overlap))
            nonzero_iou_ind=torch.nonzero(larger_ind)
            all_boxes=bboxes[nonzero_iou_ind,:].squeeze(dim=1).type(torch.cuda.IntTensor) 
            all_boxes=torch.clamp(all_boxes, min=0)
            all_boxes[:,[0,2]]=torch.clamp(all_boxes[:,[0,2]], max=image_w-1)
            all_boxes[:,[1,3]]=torch.clamp(all_boxes[:,[1,3]], max=image_h-1)
            segm_ious[i,larger_ind]=integral_image_fetch(integral_images[i],all_boxes)/integral_images[i,-1,-1]
            soft_ious[i,larger_ind]=(1+harmonic_mean_weight)/(harmonic_mean_weight/overlaps[i,larger_ind]+1/segm_ious[i,larger_ind]) 

        if plot:
            condition=[0, 0.4, 0.5, 1]
            mask_plotter(mask_aware_ious, overlaps, gt_masks, bboxes1, bboxes2, condition)

            larger_ind=overlaps>min_overlap
            nonzero_iou_ind=torch.nonzero(larger_ind)
            #gt_mask_size=torch.sum(gt_masks,dim=[1,2]).type(torch.cuda.FloatTensor)
            #end1 = time.time()
            #bboxes=bboxes.type(torch.cuda.IntTensor) 
            bboxes=torch.clamp(bboxes, min=0)
            bboxes[:,[0,2]]=torch.clamp(bboxes[:,[0,2]], max=image_w-1)
            bboxes[:,[1,3]]=torch.clamp(bboxes[:,[1,3]], max=image_h-1)

            no=random.randint(0,nonzero_iou_ind.shape[0])
            pltgt,pltanc=nonzero_iou_ind[no]
           # print(pltgt,pltanc)
            fig, ax = plt.subplots(1)
            ax.imshow(gt_masks[pltgt].cpu().numpy())

            tempRect=patch.Rectangle((bboxes[pltanc,0],bboxes[pltanc,1]), bboxes[pltanc,2]-bboxes[pltanc,0], bboxes[pltanc,3]-bboxes[pltanc,1],linewidth=3,edgecolor='r',facecolor='none')
            ax.add_patch(tempRect) 
            fntsize=14
            tempRect=patch.Rectangle((gt_bboxes[pltgt,0],gt_bboxes[pltgt,1]), gt_bboxes[pltgt,2]-gt_bboxes[pltgt,0], gt_bboxes[pltgt,3]-gt_bboxes[pltgt,1],linewidth=3,edgecolor='g',facecolor='none')
            ax.add_patch(tempRect)        

            ax.tick_params(labelsize=fntsize)      
            plt.xlabel('x', fontsize=fntsize)
            plt.ylabel('y', fontsize=fntsize)
            ax.text(0, 0, "iou= "+np.array2string(overlaps[pltgt,pltanc].cpu().numpy())+", "+\
                "\n segm_rate="+np.array2string(segm_ious[pltgt,pltanc].cpu().numpy())+", "+\
                "\n soft_iou="+np.array2string(soft_ious[pltgt,pltanc].cpu().numpy()), fontsize=12)
            plt.show()
    #end = time.time()
    #print("t=",nonzero_iou_ind.size(), end1 - start, end - start)
    return soft_ious

def segm_iou(gt_masks, gt_bboxes, bboxes, overlaps, min_overlap=0): 
    #import pdb

    #import time
    with torch.no_grad():
   # start = time.time()
        segm_ious=overlaps.data.new_zeros(overlaps.size())
        #Convert list to torch
        all_gt_masks=torch.from_numpy(gt_masks).type(torch.cuda.ByteTensor)
        gt_number,image_h,image_w=all_gt_masks.size()
        #pdb.set_trace()
        integral_images=integral_image_compute(all_gt_masks,gt_number,image_h,image_w).type(torch.cuda.FloatTensor) 
        #end1 = time.time()
        for i in range(gt_number):
            larger_ind = overlaps[i,:] > min_overlap
            nonzero_iou_ind=torch.nonzero(larger_ind)
            all_boxes=bboxes[nonzero_iou_ind,:].squeeze(dim=1).type(torch.cuda.IntTensor) 
            all_boxes=torch.clamp(all_boxes, min=0)
            all_boxes[:,[0,2]]=torch.clamp(all_boxes[:,[0,2]], max=image_w-1)
            all_boxes[:,[1,3]]=torch.clamp(all_boxes[:,[1,3]], max=image_h-1)
            segm_ious[i,larger_ind]=integral_image_fetch(integral_images[i],all_boxes)/integral_images[i,-1,-1]
    #end = time.time()
    #print("t=",nonzero_iou_ind.size(), end1 - start, end - start)
    return segm_ious

def mask_aware_bbox_overlaps(gt_masks, bboxes1, bboxes2, plot=0, overlaps=None):
    """Calculate overlap between two set of bboxes.

    If ``is_aligned`` is ``False``, then calculate the ious between each bbox
    of bboxes1 and bboxes2, otherwise the ious between each aligned pair of
    bboxes1 and bboxes2.

    Args:
        bboxes1 (Tensor): shape (m, 4)
        bboxes2 (Tensor): shape (n, 4), if is_aligned is ``True``, then m and n
            must be equal.
        mode (str): "iou" (intersection over union) or iof (intersection over
            foreground).

    Returns:
        ious(Tensor): shape (m, n) if is_aligned == False else shape (m, 1)
    """

    rows = bboxes1.size(0)
    cols = bboxes2.size(0)

    if rows * cols == 0:
        return bboxes1.new(rows, 1)

    area1 = (bboxes1[:, 2] - bboxes1[:, 0] + 1).type(torch.cuda.DoubleTensor) * (bboxes1[:, 3] - bboxes1[:, 1] + 1).type(torch.cuda.DoubleTensor)
    area2_unnorm = (bboxes2[:, 2] - bboxes2[:, 0] + 1).type(torch.cuda.DoubleTensor) * (bboxes2[:, 3] - bboxes2[:, 1] + 1).type(torch.cuda.DoubleTensor)
    lt = torch.max(bboxes1[:, None, :2], bboxes2[:, :2])  # [rows, cols, 2]
    rb = torch.min(bboxes1[:, None, 2:], bboxes2[:, 2:])  # [rows, cols, 2]

    wh = (rb - lt + 1).clamp(min=0)  # [rows, cols, 2]
    intersection_area = (wh[:, :, 0] * wh[:, :, 1]).type(torch.cuda.DoubleTensor) 

    overlap=bboxes1.data.new_zeros(rows, cols).type(torch.cuda.DoubleTensor) 
    area2=bboxes1.data.new_zeros(rows, cols).type(torch.cuda.DoubleTensor) 

    print("check1=====", torch.sum(bboxes2))
    with torch.no_grad():
        #Convert list to torch
        all_gt_masks=torch.from_numpy(gt_masks).type(torch.cuda.ByteTensor)
        gt_number,image_h,image_w=all_gt_masks.size()

        
 
        pdb.set_trace()
        integral_images=integral_image_compute(all_gt_masks,gt_number,image_h,image_w).type(torch.cuda.DoubleTensor) 
        all_boxes=torch.clamp(bboxes2, min=0)
        all_boxes[:,[0,2]]=torch.clamp(all_boxes[:,[0,2]], max=image_w-1)
        all_boxes[:,[1,3]]=torch.clamp(all_boxes[:,[1,3]], max=image_h-1)
        print("minimax",torch.min(all_boxes[:,0]),torch.min(all_boxes[:,1]),torch.max(all_boxes[:,2]),torch.max(all_boxes[:,3]), torch.sum(all_boxes))
        norm_factor=area1/integral_images[:,-1,-1]
        for i in range(gt_number):
            temp=integral_image_fetch(integral_images[i],all_boxes)
            area2[i,:]=area2_unnorm+(temp*norm_factor[i]+1)-2*intersection_area[i,:]
            overlap[i, :]=temp*norm_factor[i]
            print(i,"maxx2=", torch.max(overlap[i, :]))
        mask_aware_ious = overlap / (area1[:, None] + area2 - overlap)

    print("minimax",torch.min(all_boxes[:,0]),torch.min(all_boxes[:,1]),torch.max(all_boxes[:,2]),torch.max(all_boxes[:,3]), torch.sum(all_boxes)) 
    print("check2=====", torch.sum(bboxes2))
    if plot==1:
        cond=np.array([ 1, 2, 0, 1.])
        mask_plotter(mask_aware_ious, overlaps, gt_masks, bboxes1, bboxes2, cond)
    pdb.set_trace()
    return mask_aware_ious    