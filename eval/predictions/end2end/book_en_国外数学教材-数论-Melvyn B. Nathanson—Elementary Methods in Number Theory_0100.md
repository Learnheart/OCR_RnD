88 3. Primitive Roots and Quadratic Reciprocity

Proof: This follows immediately from Theorem 3.3, since $|\mathbb{Z}/\mathbb{Z}^*| = p - 1$. $\square$

The following table lists the primitive roots for the first six primes.

| $p$ | primitive roots |
|---|---|
| 2 | 1 |
| 3 | 1, 2 |
| 5 | 2, 3 |
| 7 | 2, 3, 5 |
| 11 | 2, 6, 7, 8 |
| 13 | 2, 6, 7, 11 |

Let $p$ be a prime, and let $g$ be a primitive root modulo $p$. If $a$ is an integer not divisible by $p$, then there exists a unique integer $k$ such that

$$
a \equiv g^k \pmod{p}
$$

and

$$
k \in \{0, 1, \dots, p - 2\}.
$$

This integer $k$ is called the index of $a$ with respect to the primitive root $g$, and is denoted by

$$
k = \operatorname{ind}_g(a).
$$

If $k_1$ and $k_2$ are any integers such that $k_1 \leq k_2$ and

$$
a \equiv g^{k_1} \equiv g^{k_2} \pmod{p},
$$

then

$$
g^{k_2 - k_1} \equiv 1 \pmod{p},
$$

and so

$$
k_2 \equiv k_1 \pmod{p - 1}.
$$

If $a \not\equiv 0 \pmod{p}$ and $b \not\equiv 0 \pmod{p}$, then $\operatorname{ind}_g(ab) \equiv k + \ell \pmod{p - 1}$, where $k = \operatorname{ind}_g(a)$ and $\ell = \operatorname{ind}_g(b)$. The index map $\operatorname{ind}_g$ is also called the discrete logarithm to the base $g$ modulo $p$.

For example, 2 is a primitive root modulo 13. Here is a table of $\operatorname{ind}_2(a)$ for $a = 1, \dots, 12$.

| $a$ | $\operatorname{ind}_2(a)$ |
|---|---|
| 1 | 0 |
| 2 | 1 |
| 3 | 2 |
| 4 | 3 |
| 5 | 4 |
| 6 | 5 |
| 7 | 6 |
| 8 | 7 |
| 9 | 8 |
| 10 | 9 |
| 11 | 10 |
| 12 | 11 |
