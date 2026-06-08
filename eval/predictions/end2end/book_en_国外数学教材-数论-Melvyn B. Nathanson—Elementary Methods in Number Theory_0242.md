234 7. Divisor Functions

$$
= 2 \sum_{1 \leqslant k \leqslant \sqrt{x}} \left\lfloor \frac{x}{k} \right\rfloor - \left\lfloor \sqrt{x} \right\rfloor^2
$$

$$
= 2 \sum_{1 \leqslant k \leqslant \sqrt{x}} \left( \frac{x}{k} - \left\{ \frac{x}{k} \right\} \right) - (\sqrt{x} - \{ \sqrt{x} \})^2
$$

$$
= 2x - 2 \sum_{1 \leqslant k \leqslant \sqrt{x}} \left( \frac{1}{k} - \left\{ \frac{x}{k} \right\} \right) - x + O(\sqrt{x})
$$

$$
= 2x + \log \sqrt{x} + 2y + O\left( \frac{1}{\sqrt{x}} \right) - x + O(\sqrt{x})
$$

$$
= x \log x + (2y - 1)x + O(\sqrt{x}).
$$

This completes the proof. ■

**Theorem 7.4** For $x \geqslant 1$,

$$
\Delta(x) = \sum_{n \leqslant x} (\log n - d(n) + 2y) = O\left( x^{1/2} \right).
$$

**Proof.** By Theorem 7.3 we have

$$
\sum_{n \leqslant x} d(n) = x \log x + (2y - 1)x + O\left( x^{1/2} \right).
$$

By Theorem 6.4 we have

$$
\sum_{n \leqslant x} \log n = x \log x - x + O(\log x).
$$

Subtracting the first equation from the second, we obtain

$$
\sum_{n \leqslant x} (\log n - d(n) + 2y) = O\left( x^{1/2} \right) - 2y[x] + O(\log x) = O\left( x^{1/2} \right).
$$

■

An ordered factorization of the positive integer $n$ into exactly $\ell$ factors is an $\ell$-tuple $(d_1, \ldots, d_\ell)$ such that $n = d_1 \cdots d_\ell$. The divisor function $d(n)$ counts the number of ordered factorizations of $n$ into exactly two factors, since each factorization $n = d\ell$ is completely determined by the first factor $d$. For every positive integer $\ell$, we define the arithmetic function $d_\ell(n)$ as the number of factorizations of $n$ into exactly $\ell$ factors. Then $d_1(n) = 1$ and $d_2(n) = d(n)$ for all $n$.
