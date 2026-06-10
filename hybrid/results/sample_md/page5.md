<table border="1" class="dataframe">
  <thead>
    <tr>
      <th>Model</th>
      <th>r</th>
      <th>p</th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <td>Unsupervised methods</td>
      <td></td>
      <td></td>
    </tr>
    <tr>
      <td>tf-idf</td>
      <td>46.77</td>
      <td>42.95</td>
    </tr>
    <tr>
      <td>Avg. GloVe embeddings</td>
      <td>32.40</td>
      <td>34.00</td>
    </tr>
    <tr>
      <td>InferSent - GloVe</td>
      <td>27.08</td>
      <td>26.63</td>
    </tr>
    <tr>
      <td>10-fold Cross-Validation</td>
      <td></td>
      <td></td>
    </tr>
    <tr>
      <td>SVR (Misra et al., 2016)</td>
      <td>63.33</td>
      <td>-</td>
    </tr>
    <tr>
      <td>SBERT-AFS-base</td>
      <td>77.20</td>
      <td>74.84</td>
    </tr>
    <tr>
      <td>SBERT-AFS-base</td>
      <td>76.57</td>
      <td>74.13</td>
    </tr>
    <tr>
      <td>SBERT-AFS-large</td>
      <td>78.68</td>
      <td>76.38</td>
    </tr>
    <tr>
      <td>SBERT-AFS-large</td>
      <td>77.85</td>
      <td>75.93</td>
    </tr>
    <tr>
      <td>Cross-Topic Evaluation</td>
      <td></td>
      <td></td>
    </tr>
    <tr>
      <td>SBERT-AFS-base</td>
      <td>58.49</td>
      <td>57.23</td>
    </tr>
    <tr>
      <td>SBERT-AFS-base</td>
      <td>52.34</td>
      <td>50.65</td>
    </tr>
    <tr>
      <td>SBERT-AFS-large</td>
      <td>62.02</td>
      <td>60.34</td>
    </tr>
    <tr>
      <td>SBERT-AFS-large</td>
      <td>53.82</td>
      <td>53.10</td>
    </tr>
  </tbody>
</table>

Table 3:Average Pearson correlation r and average Spearman's rank correlation p on the Argument Facet Similarity AFS) corpus (Misra et al.,2016).Misra et al.proposes 10-fold cross-validation. We additionally evaluate in a cross-topic scenario:Methods are trained on two topics, and are evaluated on the third topic.

tences in the same section are thematically closer than sentences in different sections. They use this to create a large dataset of weakly labeled sen tence triplets: The anchor and the positive exam ple come from the same section, while the neg ative example comes from a different section of the same article.For example, from the Alice Armold article: Anchor: Arnold joined the BBC Radio Drama Company in 1988.,positive:Arnold gained media attention in May 2012., negative: Balding and Arnold are keen amateur golfers

We use the dataset from Dor et al. We use the Triplet Objective, train SBERT for one epoch on the about 1.8 Million training triplets and evaluate it on the 222.957 test triplets. Test triplets are from a distinct set of Wikipedia articles. As evaluation metric,we use accuracyIs the positive example closer to the anchor than the negative example?

The purpose of SBERT sentence embeddings are not to be used for transfer learning for other tasks.Here we think fine-tuning BERT as de- scribed by Devlin et al. (2018) for new tasks is the more suitable method, as it updates all layers of the BERT network.However,SentEval can still give an impression on the quality of our sentence embeddings for various tasks.

We compare the SBERT sentence embeddings to other sentence embeddings methods on the fol lowing seven SentEval transfer tasks:

MRSentiment prediction for movie reviews snippets on a five start scale (Pang and Lee 2005). CRSentiment prediction of customer prod- uct reviews (Hu and Liu,2004) SUBJSubjectivity prediction of sentences from movie reviews and plot summaries Pang and Lee,2004). MPQA:Phrase level opinion polarity classi- fication from newswire (Wiebe et al.,2005). SST:Stanford Sentiment Treebank with bi- nary labels (Socher et al.,2013) TREC:Fine grained question-type classifi cation from TREC (Li and Roth.2002) MRPCMicrosoft Research Paraphrase Cor pus from parallel news sources Dolan et al. 2004).
