Figure 1: SBERT architecture with classification ob. jectivefuntionforne-tuningonSNLIdtast The two BERT networks have tied weights (siamese network structure),

computed candidate embeddings using attention. This idea works for finding the highest scoring sentence in a larger collection.However,poly- encoders have thedrawback that the score function is not symmetric and the computational overhead is too large for use-cases like clustering,which would require O（n²) score computations. Previous neural sentence embedding methods started the training from a random initialization. In this publication,we use the pre-trained BERT and RoBERTa network and only fine-tune it to yield useful sentence embeddings. This reduces significantly the needed training time: SBERT can be tuned in less than 20 minutes,while yielding better results than comparable sentence embed- dingmethods.

# 3Model

SBERT adds a pooling operation to the output ofBERT/RoBERTa to derive a fixed sized sen- tence embedding.We experiment with three pool- ing strategies:Using the output of the CLS-token, computing the mean of all output vectors (MEAN- strategy),and computing a max-over-time of the output vectors (MAX-strategy).The default config- uration is MEAN. Inorderofine-tune BERT/RoBERTawecre ate siamese and triplet networks (Schroff et al., 2015)to update the weights such that the produced sentence embeddings are semantically meaningful andcanbecomparedwith cosine-similarity The network structure depends on the available

Figure2:BERT architcture atinfrence,forexam- ple,to compute similarity scores.This architectureis also used with theregression objective function. training data. We experiment with the following structures and objective functions. Classification Objective Function, We con- catenate the sentence embeddings u and v with the element-wise difference u-u and multiply it with the trainable weight WER3nxk. 0=softmax（W（u,v,lu-ul）) where n is the dimension of the sentence em- beddings and  the number of labels.We optimize cross-entropy loss. This structure is depicted in Figure1. Regression Objective Function. The cosine- similarity between the two sentence embeddings u and v is computed (Figure 2). We use mean- squared-error loss as the objective function, Triplet Objective Function. Given an anchor sentence a,a positive sentence p,and a negative sentence n,triplet loss tunes thenetwork such that the distance between a and pis smaller than the distance between a andn.Mathematically,we minimize thefollowing loss function:

with s the sentence embedding for a/np.· a distance metric and margin e,Margin e ensures that s, is at least ecloser to sa than sn.As metric we use Euclidean distance and we set e=1 in our experiments.

# Training Details 3.1

We train SBERT on the combination of the SNLI （Bowman et al,2015）and the Multi-Genre NLI
