Table 1:Spearman rank correlation p between the cosine similarity of sentence representations ar SemEval 2012-2016,STSb:STSbenchmark,SICK-R:SICK relatedness dataset.

STS.Instead, we compute the Spearman's rank correlation between the cosine-similarity of the sentence embeddings and the gold labels.The setup for the other sentence embedding methods is equivalent, the similarity is computed by cosine similarity. The results are depicted in Table 1.

Williams et al.,2018) dataset.The SNLI is a col lection of 570,000 sentence pairs annotated with the labels contradiction, eintailment, and neu- tral. MultiNLI contains 430,000 sentence pairs and covers a range of genres of spoken and written text. We fine-tune SBERT with a 3-way softmax classifier objective function for one epoch. We used a batch-size of 16Adam optimizer with learning rate 2e-5, and a linear learning rate warm-up over 10% of thc training data. Our de- fault pooling strategy is MEAN.

The results shows that directly using the outpu of BERT leads to rather poor performances.Av- eraging the BERT embeddings achieves an aver- age correlation of only 54.81,and using the CLS token output only achieves an average correlation of 29.19.Both are worse than computing average GloVe embeddings.

4Evaluation-Semantic Textual Similarity

Using the described siamese network structure and fine-tuning mechanism substantially improves the correlation, outperforming both InferSent and Universal Sentence Encoder substantially. The only dataset where SBERT performs worse than Universal Sentence Encoder is SICK-R.Universal Sentence Encoder was trained on various datasets including news, question-answer pages and dis- cussion forums, which appears to be more suitable to the data of SICK-R. In contrast, SBERT was pre-trained only on Wikipedia (via BERT) and on NLI data.

We evaluate the performance of SBERT for com mon Semantic Textual Similarity (STS) tasks State-of-the-art methods often learn a complex regression function that maps sentence embed dings to a similarity score. However, these regres sion functions work pair-wise and due to the com- binatorial explosion those are often not scalable if the collection of sentences reaches a certain size Instead, we always use cosine-similarity to com- pare the similarity between two sentence embed dings.We ran our cxperiments also with nega tive Manhatten and negative Euclidean distances as similarity measures, but the results for all ap- proaches remained roughly the same.

While RoBERTa was able to improve the per formance for several supervised tasks, we only observe minor difference between SBERT and SRoBERTa for generating sentence embeddings.

# 4.1Unsupervised STS

# 4.2Supervised STS

The image is a cropped text excerpt from a document discussing the evaluation of SBERT for Sentence Textual Similarity (STS) tasks. It mentions using datasets like STS 2012-2016, the STS benchmark, and the SICK-Relatedness dataset, all of which provide semantic relatedness labels between 0 and 5. The text also notes that Pearson correlation is not well-suited for these tasks.

There is no tabular data encoded in the image.
