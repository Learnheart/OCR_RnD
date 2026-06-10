This diagram illustrates a neural network architecture for sentence similarity or classification. It takes two input sentences, "Sentence A" and "Sentence B", each passed through a BERT model. The BERT outputs are denoted as 'u' and 'v', respectively. These are then pooled (likely to produce fixed-length representations) and fed into a layer that computes the tuple (u, v, |u-v|). This tuple is then passed to a Softmax classifier for final output.

<table border="1" class="dataframe">
  <thead>
    <tr>
      <th>Component</th>
      <th>Input</th>
      <th>Output</th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <td>Sentence A</td>
      <td>—</td>
      <td>u</td>
    </tr>
    <tr>
      <td>Sentence B</td>
      <td>—</td>
      <td>v</td>
    </tr>
    <tr>
      <td>Pooling</td>
      <td>u</td>
      <td>u</td>
    </tr>
    <tr>
      <td>Pooling</td>
      <td>v</td>
      <td>v</td>
    </tr>
    <tr>
      <td>Feature Computation</td>
      <td>u, v</td>
      <td>(u, v, |u-v|)</td>
    </tr>
    <tr>
      <td>Softmax Classifier</td>
      <td>(u, v, |u-v|)</td>
      <td>Final Output</td>
    </tr>
  </tbody>
</table>

Figure 1:SBERT architecture with classification ob- jective function. e.gfor fine-tuning on SNLI dataset The two BERT networks have tied weights (siamese network structure).

computed candidate embeddings using attention This idea works for finding the highest scoring sentence in a Jarger collection. However, poly encoders have the drawback that the score function is not symmetric and the computational overhead is too large for use-cases like clustering, which would require O(n) score computations.

Previous neural sentence embedding method started the training from a random initialization. In this publication, we use the pre-trained BERT and RoBERTa network and only fine-tune it to yield useful sentence embeddings. This reduces significantly the needed training time: SBERT can be tuned in less than 20 minutes,while yielding better results than comparable sentence embed ding methods. 3 Model

SBERT adds a pooling operation to the outpu of BERT/RoBERTa to derive a fixed sized sen tence embedding.We experiment with three pool ing strategies: Using the output of the CLS-token computing the mean of all output vectors (MEAN- strategy). and computing a max-over-time of the output vectors (MAX-strategy).The default config uration is MEAN.

In order to fine-tune BERT/RoBERTa.we cre ate siamese and triplet networks (Schroff et al. 2015) to update the weights such that the produced sentence embeddings are semantically meaningful and can be compared with cosine-similarity

Classification Objective Function. We con catenate the sentence embeddings u and  with the element-wise difference u-v and multiply it with the trainable weight WE R3nk.

where n is the dimension of the sentence em- beddings and k the number of labels. We optimize cross-entropy loss. This structure is depicted in Figure I.

Regression Objective Function. The cosine similarity between the two sentence embeddings u and v is computed (Figure 2).We use mean squared-error loss as the objective function

Triplet Objective Function. Given an anchor sentence a,a positive sentence p, and a negative sentence n,triplet loss tunes the network such that the distance between a and p is smaller than the distance between a and n.Mathematically, we minimize the following loss function:
