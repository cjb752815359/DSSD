import cv2
import numpy as np
from datasets.pascal_voc import pascal_voc

import torch
from torch.utils.data import Dataset
try:
    from dataloaders.custom_transforms import train_transforms, test_transforms, normalize
    from mypath import Path
except:
    print('test...')
    import sys
    sys.path.extend(['G:\\CV\\Reading\\DSSD',])
    from dataloaders.custom_transforms import train_transforms, test_transforms, normalize
    from mypath import Path  


class Detection_Dataset(Dataset):

    def __init__(self, args, cfg, split='train', mode='train'):
        super().__init__()

        self.args = args
        self.cfg = cfg
        self.mode = mode
        self.input_size = int(cfg.IMAGE_SIZE)

        base_dir = Path.db_root_dir(args.dataset)
        if args.dataset == 'pascal':
            imdb = pascal_voc(base_dir=base_dir, split=split, mode=mode)
        else:
            raise NotImplementedError
        self.roidb = imdb.roidb
        self.num_classes = imdb.num_classes
        self.num_images = imdb.num_images
        # self.ratio_list, self.ration_index = self.rank_roidb_ratio()

    def rank_roidb_ratio(self):
        # rank roidb based on the ratio between width and height.
        ratio_large = 2 # largest ratio to preserve.
        ratio_small = 0.5 # smallest ratio to preserve.    
        
        ratio_list = []
        for i in range(len(self.roidb)):
            width = self.roidb[i]['width']
            height = self.roidb[i]['height']
            ratio = width / float(height)

            if ratio > ratio_large:
                self.roidb[i]['need_crop'] = 1
                ratio = ratio_large
            elif ratio < ratio_small:
                self.roidb[i]['need_crop'] = 1
                ratio = ratio_small        
            else:
                self.roidb[i]['need_crop'] = 0

            ratio_list.append(ratio)

        ratio_list = np.array(ratio_list)
        ratio_index = np.argsort(ratio_list)
        return ratio_list[ratio_index], ratio_index

    def __getitem__(self, index):
        img = cv2.imread(self.roidb[index]['image'])
        assert img is not None, 'File Not Found ' + self.roidb[index]['image']

        boxes = self.roidb[index]['boxes']  # [[x, y, w, h], ...]
        classes = self.roidb[index]['gt_classes']  # [ c, ...]
        target = np.hstack((boxes, np.expand_dims(classes, axis=1))) # [[x, y, w, h, c], ...]

        if self.mode == 'train':
            img, target = train_transforms(img, target, self.input_size)
        else:
            img, target = test_transforms(img, target, self.input_size)
 
        nL = len(target)
        if nL > 0:
            target[:, :4] = np.clip(target[:, :4], 0, self.input_size-1)
            target[:, :4] = self._xyxy2xywh(target[:, :4].copy())

            # Normalize coordinates 0 - 1
            target[:, [1, 3]] /= img.shape[0]  # height
            target[:, [0, 2]] /= img.shape[1]  # width

        # Normalize
        img = img[:, :, ::-1].transpose(2, 0, 1)  # BGR to RGB
        img = np.ascontiguousarray(img, dtype=np.float32)
        img = normalize(img)

        target_out = torch.zeros((nL, 6))
        if nL:
            target_out[:, 1:] = torch.from_numpy(target)

        img = torch.from_numpy(img).float()
        target_out = target_out.float()

        return img, target

    def _xyxy2xywh(self, x):
        # Convert bounding box format from [x1, y1, x2, y2] to [x, y, w, h]
        y = torch.zeros_like(x) if isinstance(x, torch.Tensor) else np.zeros_like(x)
        y[:, 0] = (x[:, 0] + x[:, 2]) / 2
        y[:, 1] = (x[:, 1] + x[:, 3]) / 2
        y[:, 2] = x[:, 2] - x[:, 0]
        y[:, 3] = x[:, 3] - x[:, 1]
        return y

    def __len__(self):
        return self.num_images


def show_image(img, labels):
    import matplotlib.pyplot as plt
    plt.figure(figsize=(10, 10))
    plt.subplot(1, 1, 1).imshow(img[:, :, ::-1])
    plt.plot(labels[:, [0, 2, 2, 0, 0]].T, labels[:, [1, 1, 3, 3, 1]].T, '-')
    plt.show()
    pass


if __name__ == "__main__":
    import sys
    sys.path.extend(['G:\\CV\\Reading\\DSSD',])
    from utils.config import cfg
    from utils.hyp import parse_args
    args = parse_args()
    dataset = Detection_Dataset(args, cfg)
    import torch.utils.data as data
    dataloader = data.DataLoader(dataset, batch_size=1,
                            num_workers=4, shuffle=True, pin_memory=True)
    # res = dataset.__getitem__(0)
    for (img, target) in dataloader:
        print(target) 
    pass
