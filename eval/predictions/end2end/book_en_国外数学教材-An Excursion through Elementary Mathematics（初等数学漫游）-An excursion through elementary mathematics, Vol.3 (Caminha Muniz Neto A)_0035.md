Moreover, for $1 \leq k \leq n$ such numbers satisfy the recurrence relation

$$
\binom{n}{k} = \binom{n-1}{k-1} + \binom{n-1}{k}
$$

which is known as Stiefel’s relation and allows us to prove that $C_n^k = \binom{n}{k}$ for every $n$ and $k$ as above.

Proposition 1.26. If $A$ is a finite set with $n$ elements and $0 \leq k \leq n$, then $A$ possesses exactly $\binom{n}{k}$ subsets of $k$ elements.

Proof. If $k = 0$, there is nothing to do, for the only subset of $A$ having $0$ elements is $\emptyset$. Thus, let $1 \leq k \leq n$ and $C_n^k$ be the number of subsets of $A$ with $k$ elements.

For a fixed $x \in A$, there are two kinds of subsets of $A$ with $k$ elements: those which do not contain $x$ and those which do contain $x$. The former ones are precisely the $k$-element subsets of $A \setminus \{x\}$; since $|A \setminus \{x\}| = n - 1$, there are exactly $C_{n-1}^k$ of these subsets of $k$ elements.

On the other hand, if $B \subset A$ has $k$ elements and $x \in B$, then $B \setminus \{x\} \subset A$ has $k - 1$ elements; conversely, if $B' \subset A$ has $k - 1$ elements, then $B' \cup \{x\} \subset A$ has $k$ elements, one of which is $B$. Since such correspondences are clearly inverses of each other, we conclude that there are as many $k$-element subsets of $A$ containing $x$ as there are $k - 1$-element subsets of $A \setminus \{x\}$. These are exactly $C_{n-1}^{k-1}$ such $k$-element subsets of $A$.

Taking these two contributions into account, we obtain for $1 \leq k \leq n$ the recurrence relation

$$
C_n^k = C_{n-1}^k + C_{n-1}^{k-1},
$$

which is identical to Stiefel’s relation for the binomial coefficients. Finally, since $C_n^0 = 1$ and $C_n^n = 1$, with $C_n^0 = C_n^n = 1$ (for $n \geq 0$), we have

$$
C_n^k = \binom{n}{k}, \quad \text{with a } k \text{ as an easy induction gives } C_n^k = \binom{n}{k} \text{ for } 0 \leq k \leq n.
$$

In words, the previous proposition computes how many are the unordered choices of $k$ distinct elements of a set having $n$ elements; one uses to say that such choices are the combinations of $k$ objects, taken $k$ at a time. Also, thanks to the former proposition, one uses to refer to the binomial coefficient $\binom{n}{k}$ as “$n$ choose $k$”.

Example 1.27. When all diagonals of a certain convex octagon have been drawn, one notices that there were no more than three passing through a single interior point of the octagon. How many points of the interior of the octagon are intersection points of two of its diagonals?

Solution. Firstly, note that the condition on the diagonals of the octagon guarantees that each of the points of intersection we wish to count is determined by a single pair of diagonals. Hence, it suffices to count how many pairs of diagonals of the octagon intersect in its interior. To this end, note that each 4-element subset of
