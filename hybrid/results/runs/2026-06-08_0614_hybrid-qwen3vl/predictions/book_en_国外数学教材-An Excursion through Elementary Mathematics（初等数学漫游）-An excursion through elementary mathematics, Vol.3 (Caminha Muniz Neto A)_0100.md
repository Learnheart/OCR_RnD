$$
\frac{1 - 2x + 2x^2}{(1 - x)^3(1 - 2x)} = \frac{A}{1 - x} + \frac{B}{(1 - x)^2} + \frac{C}{1 - 2x}
$$

(d) Expand each summand of the right hand side above as a power series to conclude that $ a_n = 2^{n+1} - (n + 1) $, for $ n \geq 0 $.

3. Given $ k \in \mathbb{N} $, use generating functions to compute the number of integer solutions of the equation $ a_1 + a_2 + \cdots + a_k = n $, such that $ a_i \geq 2 $, satisfying $ a_1 \geq a_2 \geq \cdots \geq a_k $.

4. A particle moves on the cartesian plane in such a way that from point $ (a, b) $ it can go to either $ (a + 1, b) $ or $ (a, b + 1) $. Given $ n \in \mathbb{N} $, let $ a_n $ be the number of distinct paths that the particle can go from $ A(0, 0) $ to $ B(n, n) $, without ever touching the point $ (x, y) $ situated above the bisector of quadrants (i.e., each one such point for which $ y > x $). In this respect, do the following items:

(a) Let $ A_n(l, k) $, with $ 0 \leq l \leq k \leq n $, be the number of distinct trajectories for the particle in which $ A_k $ is the last point (before $ A_n $) on the line $ y = x $.

(b) Conclude that $ a_n = \sum_{k=0}^n \sum_{l=0}^k A_n(l, k) $, and hence, that there are exactly $ a_{n-1} + a_{n-2} $ distinct trajectories for the particle in which $ A_k $ is the last point (before $ A_n $) on the line $ y = x $.

(c) Conclude that $ a_n = \sum_{k=0}^n \sum_{l=0}^k A_n(l, k) $, and hence, that there are exactly $ a_{n-1} + a_{n-2} $ distinct trajectories for the particle in which $ A_k $ is the last point (before $ A_n $) on the line $ y = x $.

5. For the counting problem above, the reader may find it convenient to read again the problem for computing Example 1.15.

6. For $ n \in \mathbb{N} $, let $ a_n $ denote the number of partitions of $ n $ in natural summands, none of which exceeds 3. The purpose of this problem is to compute $ a_n $ as a function of $ n $, and to find the closed form for this function.

(a) Show that, for $ |x| < 1 $, one has

$$
\sum_{n=0}^{\infty} a_n x^n = \frac{1}{(1 - x)(1 - x^2)(1 - x^3)} = \frac{a}{1 - x} + \frac{b}{1 - x^2} + \frac{c}{1 - x^3}
$$

(b) Find $ a, b, c \in \mathbb{R} $ for which

$$
\frac{1}{(1 - x)(1 - x^2)(1 - x^3)} = \frac{a}{1 - x} + \frac{b}{1 - x^2} + \frac{c}{1 - x^3}
$$

(c) Conclude that

$$
a_n = \begin{cases}
\left\lfloor \frac{n^2}{12} \right\rfloor + 1 & \text{if } n \equiv 0 \pmod{6} \\
\left\lfloor \frac{n^2}{12} \right\rfloor + 1 & \text{if } n \equiv 1 \pmod{6} \\
\left\lfloor \frac{n^2}{12} \right\rfloor + 1 & \text{if } n \equiv 2 \pmod{6} \\
\left\lfloor \frac{n^2}{12} \right\rfloor + 1 & \text{if } n \equiv 3 \pmod{6} \\
\left\lfloor \frac{n^2}{12} \right\rfloor + 1 & \text{if } n \equiv 4 \pmod{6} \\
\left\lfloor \frac{n^2}{12} \right\rfloor + 1 & \text{if } n \equiv 5 \pmod{6}
\end{cases}
$$
