186 Chapter 7. The Zeta Function and Prime Number Theorem

which holds for $0 \leq x < 1$, we find that

$$
\log \zeta(s) = \log \sum_{n=1}^{\infty} \frac{1}{n^s} = \sum_{n=1}^{\infty} \log \left( \frac{1}{1 - n^{-s}} \right) = \sum_{n=1}^{\infty} \sum_{k=1}^{\infty} \frac{1}{k} n^{-ks}.
$$

Since the double sum converges absolutely, we need not specify the order of summation. See the Note at the end of this chapter. The formula then holds for all $\operatorname{Re}(s) > 1$ by analytic continuation. Note that, by Theorem 6.2 in Chapter 3, $\log \zeta(s)$ is well defined in the simply connected half-plane $\operatorname{Re}(s) > 1$, since $\zeta(s)$ has no zeros there. Finally, it is clear that we have

$$
\log \zeta(s) = \sum_{n=1}^{\infty} \frac{1}{n} \sum_{k=1}^{\infty} \frac{1}{k} n^{-ks},
$$

where $\alpha_n = 1$ if $n = p^k$ and $\alpha_n = 0$ otherwise.

The proof of the theorem we shall give depends on a simple trick that is based on the following inequality.

Lemma 1.4 If $\theta \in \mathbb{R}$, then $3 + 4 \cos \theta + \cos 2\theta \geq 0$.

This follows at once from the simple observation

$$
3 + 4 \cos \theta + \cos 2\theta = 2(1 + \cos^2 \theta) + 2 \cos \theta.
$$

Corollary 1.5 If $p > 1$ and $s$ is real, then

$$
\log | \zeta(s) |^p = p \log | \zeta(s) | = p \log \left( \sum_{n=1}^{\infty} \frac{1}{n^s} \right) \geq 0.
$$

Proof. Let $s = \sigma + it$ and note that

$$
\operatorname{Re}(\zeta(s)) = \zeta(\sigma) - i \sum_{n=1}^{\infty} \frac{\sin(\pi n t)}{n^{\sigma}} = e^{-t \log n} \cos(\pi n t) = n^{-\sigma} \cos(\pi n t).
$$

Therefore,

$$
\log | \zeta(s) |^p = p \log | \zeta(s) | = p \log \left( \sum_{n=1}^{\infty} \frac{1}{n^s} \right)
$$

$$
= 3 \log | \zeta(s) | + 4 \log | \zeta(s) | + \log | \zeta(s) + 2\theta |
$$

$$
= 2 \operatorname{Re} \log | \zeta(s) | + 4 \operatorname{Re} \log | \zeta(s) + 2\theta | + \operatorname{Re} \log | \zeta(s) + 2\theta |
$$

$$
= \sum_{n=1}^{\infty} \alpha_n (3 + 4 \cos \theta_n + \cos 2\theta_n),
$$

where $\theta_n = t \log n$. The positivity now follows from Lemma 1.4, and the fact that $\alpha_n \geq 0$.
