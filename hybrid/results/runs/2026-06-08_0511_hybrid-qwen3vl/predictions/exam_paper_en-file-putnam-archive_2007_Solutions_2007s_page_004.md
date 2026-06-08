B-2 Part 4: $m_{\text{max}}(p^{\alpha})$ and $g(p^{\alpha})$ for $p \in \mathbb{Z}$, since $g(p^{\alpha}) = 0$ if $\alpha = 0$, the maximum value of $g(p^{\alpha})$ must occur at a critical point of $g(p^{\alpha})$ satisfying $\frac{d}{d\alpha} g(p^{\alpha}) = 0$. We may thus take $\alpha = 1$; henceforth,

Since $\frac{d}{d\alpha} g(p^{\alpha}) = -\frac{1}{2} \sum_{k=1}^{\infty} \frac{1}{k} p^{-k\alpha}$, we may assume that $\alpha = 1/2$. By then substituting $g(p^{\alpha})$ for $g(p)$, we find that $\frac{d}{d\alpha} g(p^{\alpha}) = 0$ when $\sum_{k=1}^{\infty} \frac{1}{k} p^{-k\alpha} = 0$. From the inequality $p^{-k\alpha} \leq p^{-k}$, we deduce $g(p^{\alpha}) \leq g(p)$ for $0 \leq \alpha \leq 1$. Thus,

$$
\int_{0}^{1} \int_{0}^{1} f(x,y) \, dx \, dy = \int_{0}^{1} f(x,0) \, dx + \int_{0}^{1} f(x,1) \, dx.
$$

B-3 First solution: Observing that $\alpha_1 = 1/2$, $\alpha_2 = 3/4$, $\alpha_3 = 5/8$, we see that $\alpha_n = \frac{2n-1}{2^n}$, where $n \in \mathbb{N}$. We thus have that $\alpha_n = \frac{2n-1}{2^n} = \frac{1}{2^{n-1}} - \frac{1}{2^n}$, so that

$$
\sum_{n=1}^{\infty} \alpha_n = \sum_{n=1}^{\infty} \left( \frac{1}{2^{n-1}} - \frac{1}{2^n} \right) = 2.
$$

We prove the claim by induction: the base case is $n = 1$, and since $\alpha_1 = 1/2$, we see that the sum is $1/2$. Assume that $\sum_{k=1}^{n} \alpha_k = \frac{2n-1}{2^n}$ is satisfied for our formula for $n$. Indeed, since $\alpha_{n+1} = \frac{2(n+1)-1}{2^{n+1}} = \frac{2n+1}{2^{n+1}}$, we have

$$
\sum_{k=1}^{n+1} \alpha_k = \sum_{k=1}^{n} \alpha_k + \alpha_{n+1} = \frac{2n-1}{2^n} + \frac{2n+1}{2^{n+1}} = \frac{4n-2 + 2n+1}{2^{n+1}} = \frac{6n-1}{2^{n+1}}.
$$

Now $2^{n+1} \alpha_{n+1} = (2^{n+1}) \cdot \frac{2n+1}{2^{n+1}} = 2n+1$, and the recursion follows since $\alpha_{n+1} = \frac{2n+1}{2^{n+1}}$.

Second solution: By Cauchy's first inequality, we have

$$
\sum_{k=1}^{\infty} \alpha_k \leq \sum_{k=1}^{\infty} \frac{1}{k} = \infty.
$$

But since $\alpha_k = \frac{2k-1}{2^k}$, we have

$$
\sum_{k=1}^{\infty} \alpha_k = \sum_{k=1}^{\infty} \left( \frac{1}{2^{k-1}} - \frac{1}{2^k} \right) = 2.
$$

Remark: With an initial $1$ prepended, this becomes sequence A008849 in Sloane's Online Encyclopedia of Integer Sequences (http://www.research.att.com/~njas/).

B-4 The number of pairs $(x,y)$ such that $x \equiv y \pmod{p}$ is the least integer for which $m_{\text{max}}(p^{\alpha}) > 0$; hence, since $m_{\text{max}}(p^{\alpha}) = 0$ for all $\alpha > 0$, the maximum value of $m_{\text{max}}(p^{\alpha})$ is $0$. We may thus take $\alpha = 1$; henceforth,

Since $\frac{d}{d\alpha} m_{\text{max}}(p^{\alpha}) = -\frac{1}{2} \sum_{k=1}^{\infty} \frac{1}{k} p^{-k\alpha}$, we may assume that $\alpha = 1/2$. By then substituting $m_{\text{max}}(p^{\alpha})$ for $m_{\text{max}}(p)$, we find that $\frac{d}{d\alpha} m_{\text{max}}(p^{\alpha}) = 0$ when $\sum_{k=1}^{\infty} \frac{1}{k} p^{-k\alpha} = 0$. From the inequality $p^{-k\alpha} \leq p^{-k}$, we deduce $m_{\text{max}}(p^{\alpha}) \leq m_{\text{max}}(p)$ for $0 \leq \alpha \leq 1$. Thus,

$$
\int_{0}^{1} \int_{0}^{1} f(x,y) \, dx \, dy = \int_{0}^{1} f(x,0) \, dx + \int_{0}^{1} f(x,1) \, dx.
$$

B-5 For an integer $n$, we have $\sum_{k=1}^{n} k = \frac{n(n+1)}{2}$.

B-6 For an integer $n$, we have $\sum_{k=1}^{n} k^2 = \frac{n(n+1)(2n+1)}{6}$.

B-7 For an integer $n$, we have $\sum_{k=1}^{n} k^3 = \left( \frac{n(n+1)}{2} \right)^2$.

B-8 For an integer $n$, we have $\sum_{k=1}^{n} k^4 = \frac{n(n+1)(2n+1)(3n^2+3n-1)}{30}$.

B-9 For an integer $n$, we have $\sum_{k=1}^{n} k^5 = \frac{n^2(n+1)^2(2n^2+2n-1)}{12}$.

B-10 For an integer $n$, we have $\sum_{k=1}^{n} k^6 = \frac{n(n+1)(2n+1)(3n^4+6n^3-3n+1)}{42}$.

B-11 For an integer $n$, we have $\sum_{k=1}^{n} k^7 = \frac{n^2(n+1)^2(3n^4+6n^3-3n^2+2n-1)}{24}$.

B-12 For an integer $n$, we have $\sum_{k=1}^{n} k^8 = \frac{n(n+1)(2n+1)(5n^6+15n^5+5n^4-15n^3+3n^2-3n+1)}{90}$.

B-13 For an integer $n$, we have $\sum_{k=1}^{n} k^9 = \frac{n^2(n+1)^2(3n^6+9n^5-3n^4-9n^3+3n^2-3n+1)}{24}$.

B-14 For an integer $n$, we have $\sum_{k=1}^{n} k^{10} = \frac{n(n+1)(2n+1)(3n^8+12n^7+6n^6-24n^5+6n^4-12n^3+3n^2-3n+1)}{90}$.

B-15 For an integer $n$, we have $\sum_{k=1}^{n} k^{11} = \frac{n^2(n+1)^2(5n^8+20n^7+10n^6-40n^5+10n^4-20n^3+5n^2-5n+1)}{24}$.

B-16 For an integer $n$, we have $\sum_{k=1}^{n} k^{12} = \frac{n(n+1)(2n+1)(3n^{10}+15n^9+5n^8-30n^7+5n^6-30n^5+5n^4-30n^3+5n^2-30n+1)}{90}$.

B-17 For an integer $n$, we have $\sum_{k=1}^{n} k^{13} = \frac{n^2(n+1)^2(7n^{10}+35n^9+21n^8-70n^7+21n^6-70n^5+21n^4-70n^3+21n^2-70n+1)}{24}$.

B-18 For an integer $n$, we have $\sum_{k=1}^{n} k^{14} = \frac{n(n+1)(2n+1)(3n^{12}+21n^{11}+15n^{10}-63n^9+15n^8-63n^7+15n^6-63n^5+15n^4-63n^3+15n^2-63n+1)}{90}$.

B-19 For an integer $n$, we have $\sum_{k=1}^{n} k^{15} = \frac{n^2(n+1)^2(11n^{12}+66n^{11}+44n^{10}-132n^9+44n^8-132n^7+44n^6-132n^5+44n^4-132n^3+44n^2-132n+1)}{24}$.

B-20 For an integer $n$, we have $\sum_{k=1}^{n} k^{16} = \frac{n(n+1)(2n+1)(3n^{14}+28n^{13}+21n^{12}-84n^{11}+21n^{10}-84n^9+21n^8-84n^7+21n^6-84n^5+21n^4-84n^3+21n^2-84n+1)}{90}$.

B-21 For an integer $n$, we have $\sum_{k=1}^{n} k^{17} = \frac{n^2(n+1)^2(13n^{14}+91n^{13}+65n^{12}-208n^{11}+65n^{10}-208n^9+65n^8-208n^7+65n^6-208n^5+65n^4-208n^3+65n^2-208n+1)}{24}$.

B-22 For an integer $n$, we have $\sum_{k=1}^{n} k^{18} = \frac{n(n+1)(2n+1)(3n^{16}+36n^{15}+27n^{14}-108n^{13}+27n^{12}-108n^{11}+27n^{10}-108n^9+27n^8-108n^7+27n^6-108n^5+27n^4-108n^3+27n^2-108n+1)}{90}$.

B-23 For an integer $n$, we have $\sum_{k=1}^{n} k^{19} = \frac{n^2(n+1)^2(17n^{16}+136n^{15}+102n^{14}-340n^{13}+102n^{12}-340n^{11}+102n^{10}-340n^9+102n^8-340n^7+102n^6-340n^5+102n^4-340n^3+102n^2-340n+1)}{24}$.

B-24 For an integer $n$, we have $\sum_{k=1}^{n} k^{20} = \frac{n(n+1)(2n+1)(3n^{18}+45n^{17}+36n^{16}-135n^{15}+36n^{14}-135n^{13}+36n^{12}-135n^{11}+36n^{10}-135n^9+36n^8-135n^7+36n^6-135n^5+36n^4-135n^3+36n^2-135n+1)}{90}$.

B-25 For an integer $n$, we have $\sum_{k=1}^{n} k^{21} = \frac{n^2(n+1)^2(19n^{18}+152n^{17}+114n^{16}-380n^{15}+114n^{14}-380n^{13}+114n^{12}-380n^{11}+114n^{10}-380n^9+114n^8-380n^7+114n^6-380n^5+114n^4-380n^3+114n^2-380n+1)}{24}$.

B-26 For an integer $n$, we have $\sum_{k=1}^{n} k^{22} = \frac{n(n+1)(2n+1)(3n^{20}+55n^{19}+44n^{18}-165n^{17}+44n^{16}-165n^{15}+44n^{14}-165n^{13}+44n^{12}-165n^{11}+44n^{10}-165n^9+44n^8-165n^7+44n^6-165n^5+44n^4-165n^3+44n^2-165n+1)}{90}$.

B-27 For an integer $n$, we have $\sum_{k=1}^{n} k^{23} = \frac{n^2(n+1)^2(23n^{20}+207n^{19}+155n^{18}-585n^{17}+155n^{16}-585n^{15}+155n^{14}-585n^{13}+155n^{12}-585n^{11}+155n^{10}-585n^9+155n^8-585n^7+155n^6-585n^5+155n^4-585n^3+155n^2-585n+1)}{24}$.

B-28 For an integer $n$, we have $\sum_{k=1}^{n} k^{24} = \frac{n(n+1)(2n+1)(3n^{22}+66n^{21}+55n^{20}-220n^{19}+55n^{18}-220n^{17}+55n^{16}-220n^{15}+55n^{14}-220n^{13}+55n^{12}-220n^{11}+55n^{10}-220n^9+55n^8-220n^7+55n^6-220n^5+55n^4-22
