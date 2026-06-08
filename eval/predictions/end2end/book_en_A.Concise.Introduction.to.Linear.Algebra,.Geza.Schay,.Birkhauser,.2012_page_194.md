$$S(x) = \begin{bmatrix} x_1 + x_2 \\ x_1 - x_2 \end{bmatrix} \tag{4.62}$$

$$T(x) = \begin{bmatrix} x_1 - x_2 \\ x_1 + x_2 \end{bmatrix} \tag{4.63}$$

Then $Q = S + T$ and $R = cT$ are the linear transformations given by

$$Q(x) = \begin{bmatrix} 2x_1 \\ 2x_2 \end{bmatrix} \tag{4.64}$$

$$R(x) = \begin{bmatrix} c(x_1 - x_2) \\ c(x_1 + x_2) \end{bmatrix} \tag{4.65}$$

With Definition 4.2.4 Theorems 4.2.8 and 4.2.9 lead to the following theorem.

**Theorem 4.2.10. (The Linear Transformations from $U$ to $V$ Form a Vector Space, Which Is Isomorphic to $M_{m,n}$.)** Let $L(U,V)$ denote the set of all linear transformations from an $n$-dimensional vector space $U$ to an $m$-dimensional vector space $V$, and let $A = (a_{ij})_{m \times n}$ be an ordered basis for $U$, $B = (b_1, b_2, \dots, b_m)$ an ordered basis for $V$, and $T_{A,B}$ the $m \times n$ matrix that represents any $T \in L(U,V)$ relative to these bases. Then

1. $L(U,V)$, together with addition and scalar multiplication of transformations as in Definition 4.2.4, is a vector space.

2. The mapping $M$ from $L(U,V)$ to the vector space $M_{m,n}$ of all $m \times n$ matrices given by $M(T) = T_{A,B}$ is linear and an isomorphism. Hence $L(U,V)$ is an $m$-dimensional vector space.

**Proof.** $L(U,V)$ is clearly nonzero; the zero mapping $O$ in it. Theorem 4.2.8 shows that $L(U,V)$ is closed under addition and multiplication by scalars. The vector space axioms for $L(U,V)$ follow from the corresponding ones in $V$ for every $x$ in $U$ (see 4.2.8). In particular, the zero element is the zero mapping, and the element $-T$ is the mapping $(-1)T$.

Let $S, T \in L(U,V)$ and $a, b$ any scalars. Then by Theorem 4.1.3, for all $x \in U$, $(S + T)(x) = S(x) + T(x)$ becomes

$$y_D = (aS + bT)_{A,B}x_A = M(aS + bT)x_A \tag{4.66}$$

$^{\text{a}}$ See Example 3.1.2.
