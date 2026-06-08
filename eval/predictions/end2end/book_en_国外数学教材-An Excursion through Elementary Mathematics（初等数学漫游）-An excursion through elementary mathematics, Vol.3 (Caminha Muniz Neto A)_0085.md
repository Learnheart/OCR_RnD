$$
x^{n} = \sum_{k=0}^{n} \binom{n}{k} x^{k} \quad (3.8)
$$

For every $ x \in \mathbb{R} $.

A variation of the argument used in Example 3.8 allows us to expand $ f(x) = (1 + x)^{p} $ in power series when $ p \in \mathbb{R} $ and $ x \in [-1, 1] $ for a fixed real number $ p \neq 0 $. To this end, given $ a \in \mathbb{R} $ and $ n \in \mathbb{N} $, we begin by defining the generalized binomial number $ \binom{a}{n} $ by letting $ \binom{a}{0} = 1 $ and, for $ n \geq 1 $,

$$
\binom{a}{n} = \frac{a(a - 1)(a - 2) \cdots (a - n + 1)}{n!} \quad (3.9)
$$

**Lemma 3.9** Given $ a \in \mathbb{R} $ and $ n \in \mathbb{N} $, we have:

(a) $ \binom{a}{n} = \binom{a}{n-1} + \binom{a}{n} $.

(b) $ \sum_{k=0}^{n} \binom{a}{k} = \binom{a+1}{n+1} $, for every $ a \in \mathbb{R} $.

(c) $ \left| \binom{a}{n} \right| \leq 1 $ whenever $ n \geq 1 $.

**Proof**

(a) Is an easy computation:

$$
\binom{a}{n} - \binom{a-1}{n} = \frac{1}{n!} (a - 1)(a - 2) \cdots (a - n + 1)
$$

$$
- \frac{1}{n!} (a - 1)(a - 2) \cdots (a - n)
$$

$$
= \frac{1}{n!} (a - 1)(a - 2) \cdots (a - n + 1) \left[ 1 - \frac{a - n}{a} \right]
$$

$$
= \frac{1}{n!} (a - 1)(a - 2) \cdots (a - n + 1) \cdot \frac{n}{a}
$$

$$
= \binom{a-1}{n-1} \cdot \frac{a - n + 1}{a}
$$

(b) Follows immediately from (3.9).

(c) If $ |a| \leq 1 $, it follows from (3.9) and the triangle inequality that

$$
\left| \binom{a}{n} \right| \leq \frac{1}{n!} (|a| + 1)(|a| + 2) \cdots (|a| + n - 1) \leq \frac{1 \cdot 2 \cdots n}{n!} = 1.
$$
