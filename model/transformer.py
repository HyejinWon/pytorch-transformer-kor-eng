import torch
import torch.nn as nn

from model.encoder import Encoder
from model.decoder import Decoder


class Transformer(nn.Module):
    def __init__(self, params):
        super(Transformer, self).__init__()
        self.params = params
        self.device = params.device
        self.encoder = Encoder(params)
        self.decoder = Decoder(params)

    def create_subsequent_mask(self, target):
        # target = [batch size, target length]

        batch_size, target_length = target.size()

        # torch.triu returns the upper triangular part of a matrix based on user defined diagonal
        '''
        if target length is 5 and diagonal is 1, this function returns
            [[0, 1, 1, 1, 1],
             [0, 0, 1, 1, 1],
             [0, 0, 0, 1, 1],
             [0, 0, 0, 0, 1],
             [0, 0, 0, 0, 1]]
        '''
        subsequent_mask = torch.triu(torch.ones(target_length, target_length), diagonal=1).bool().to(self.device)
        # subsequent_mask = [target length, target length]

        # clone subsequent mask 'batch size' times to cover all data instances in the batch
        subsequent_mask = subsequent_mask.unsqueeze(0).repeat(batch_size, 1, 1)
        # subsequent_mask = [batch size, target length, target length]

        return subsequent_mask

    def create_mask(self, source, target, subsequent_mask):
        # source          = [batch size, source length]
        # target          = [batch size, target length]
        # subsequent_mask = [batch size, target length, target length]
        source_length = source.shape[1]
        target_length = target.shape[1]

        # create boolean tensors which will be used to mask padding tokens of both source and target sentence
        source_mask = (source == self.params.pad_idx)
        target_mask = (target == self.params.pad_idx)
        # source mask    = [batch size, source length]
        # target mask    = [batch size, target length]

        # repeat source sentence masking tensor 'target sentence length' times: dec_enc_mask
        dec_enc_mask = source_mask.unsqueeze(1).repeat(1, target_length, 1)
        # repeat source sentence masking tensor 'source sentence length' times: source_mask
        source_mask = source_mask.unsqueeze(1).repeat(1, source_length, 1)
        # repeat target sentence masking tensor 'target sentence length' times: target_mask
        target_mask = target_mask.unsqueeze(1).repeat(1, target_length, 1)
        # dec enc mask   = [batch size, target length, source length]
        # source mask    = [batch size, source length, source length]
        # target mask    = [batch size, target length, target length]

        # combine pad token masking tensor and subsequent masking tensor for decoder's self attention
        target_mask = target_mask | subsequent_mask
        # target mask = [batch size, target length, target length]

        return source_mask, target_mask, dec_enc_mask

    def forward(self, source, target):
        # source = [batch size, source length]
        # target = [batch size, target length]

        # create masking tensor for self attention (encoder & decoder) and decoder's attention on the output of encoder
        subsequent_mask = self.create_subsequent_mask(target)
        source_mask, target_mask, dec_enc_mask = self.create_mask(source, target, subsequent_mask)

        source = self.encoder(source, source_mask)
        output = self.decoder(target, source, target_mask, dec_enc_mask)
        # output = [batch size, target length, output dim]

        return output

    def count_parameters(self):
        return sum(p.numel() for p in self.parameters() if p.requires_grad)
