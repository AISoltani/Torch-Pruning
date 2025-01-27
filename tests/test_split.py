# Import Libraries

import sys, os
import torch
import torch_pruning as tp
import torch.nn as nn

sys.path.append(os.path.dirname(os.path.dirname(os.path.realpath(__file__))))



class Net(nn.Module):
    def __init__(self, in_dim):
        super().__init__()
        
        self.block1 = nn.Sequential(
            nn.Conv2d(in_dim, in_dim, 1),
            nn.BatchNorm2d(in_dim),
            nn.GELU(),
            nn.Conv2d(in_dim, in_dim*3, 1),
            nn.BatchNorm2d(in_dim*3)
        )

        self.block2_1 = nn.Sequential(
            nn.Conv2d(in_dim, in_dim, 1),
            nn.BatchNorm2d(in_dim)
        )

        self.block2_2 = nn.Sequential(
            nn.Conv2d(2*in_dim, in_dim, 1),
            nn.BatchNorm2d(in_dim)
        )
        
    def forward(self, x):
        x = self.block1(x)
        num_ch = x.shape[1]
        
        c1, c2 = self.block2_1[0].in_channels, self.block2_2[0].in_channels
        x1, x3 = torch.split(x, [c1, c2], dim=1)
        x1 = self.block2_1(x1)
        #x2 = self.block2_1(x2)
        x3 = self.block2_2(x3)
        return x1, x3
    
def test_pruner():
    model = Net(10)
    print(model)
    # Global metrics
    example_inputs = torch.randn(1, 10, 7, 7)
    imp = tp.importance.RandomImportance()
    ignored_layers = []

    # DO NOT prune the final classifier!
    for m in model.modules():
        if isinstance(m, torch.nn.Linear) and m.out_features == 1000:
            ignored_layers.append(m)

    iterative_steps = 1
    pruner = tp.pruner.MagnitudePruner(
        model,
        example_inputs,
        importance=imp,
        iterative_steps=iterative_steps,
        ch_sparsity=0.5, # remove 50% channels, ResNet18 = {64, 128, 256, 512} => ResNet18_Half = {32, 64, 128, 256}
        ignored_layers=ignored_layers,
    )
    for g in pruner.DG.get_all_groups():
        pass
    base_macs, base_nparams = tp.utils.count_ops_and_params(model, example_inputs)
    for i in range(iterative_steps):
        for g in pruner.step(interactive=True):
            print(g.details())
            g.prune()
        print(model)
        macs, nparams = tp.utils.count_ops_and_params(model, example_inputs)
        
        print([o.shape for o in model(example_inputs)])
        print(
            "  Iter %d/%d, Params: %.2f => %.2f"
            % (i+1, iterative_steps, base_nparams, nparams)
        )
        print(
            "  Iter %d/%d, MACs: %.2f => %.2f"
            % (i+1, iterative_steps, base_macs, macs )
        )
        # finetune your model here
        # finetune(model)
        # ...

if __name__=='__main__':
    test_pruner()
