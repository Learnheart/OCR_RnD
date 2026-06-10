SemEval2012-2016,STSb:STSbenchmark,SICK-R:SICKrlatedness dataset

(Williamset al.,2018)dataset.TheSNLI isacol- lection of570.000 sentence pairs annotated with the labels contradiction,eintailment,and neu- tral.MultiNLI contains 430.000 sentence pairs and covers a range ofgenresof spoken andwritten text.We fine-tune SBERTwith a3-way softmax- classifier objective function for one epoch. We used a batch-size of 16,Adam optimizer with learning rate 2e-5,and a linear learning rate warm-up over 10% of the training data. Our de- fault pooling strategy isMEAN.

# Evaluation-SemanticTextual 4 Similarity

We evaluate theperformance ofSBERTforcom- mon Semantic Textual Similarity (STS) tasks. State-of-the-art methods often learn a (complex) regression function that maps sentence embed- dings to a similarity score.However,theseregres- sion functionswork pair-wise and due to the com- binatorial explosion those are oftennot scalableif the collection of sentences reaches a certain size. Instead,we always use cosine-similarity to com- pare the similarity between two sentence embed- dings. We ran our cxperiments also with nega- tive Manhatten and negative Euclidean distances as similarity measures,but the results for all ap- proaches remained roughly the same.

# 4.1Unsupervised STS

We evaluate the performance of SBERT for STS without using any STS specific training data.We use the STS tasks 2012-2016（Agirre et al.,2012. 2013,2014,2015.2016).theSTSbenchmark(Cer el al,2017）.and the SICK-Relatedness dalaset （Marellital,2014）.These datasets provide la bels between O and5on the semantic relatedness of sentence pairs. We showed in Reimers et al, 2016) that Pearson correlation is badly suited for

STS.Instead,we compute the Spearman’s rank correlation between the cosine-similarity of the sentence embeddings and the gold labels. The setup for the other sentence embedding methods isequivalent,the similarityiscomputedbycosine similarity.The results are depicted in Table 1. The results shows that directly using the output of BERT leads to rather poor performances.Av- eraging the BERT embeddings achieves an aver- age correlation of only 54.81,and using the CLS- token output only achieves an average correlation of29.19.Both areworsethan computing average GloVe embeddings. Using the described siamese network structure and fine-tuningmechanism substantiallyimproves the correlation,outperforming both InferSent and Universal Sentence Encoder substantially.The only dataset where SBERT performs worse than Universal Sentence Encoderis SICK-R.Universal Sentence Encoder was trained onvarious datasets, including news, question-answer pages and dis- cussionforums,whichappears tobemore suitable to the data of SICK-R.In contrast,SBERT was pre-trained only on Wikipedia (via BERT) and on NLI data. WhileRoBERTa was able to improve the per- formance for several supervised tasks,we only observe minor difference between SBERT and SRoBERTa for generating sentence embeddings.

# 4.2 Supervised STS

TheSTS benchmark(STSb)(Cer et al.,2017)pro- vides is a popular dataset to evaluate supervised STS systems.The data includes 8.628 sentence pairsfrom hethreecatgoriescationsewsn forums.It is divided into train(5.749),dev(1,500) and test(1,379).BERT set a new state-of-the-art performance on this dataset by passing both sen- tences to the network and using a simple regres-
