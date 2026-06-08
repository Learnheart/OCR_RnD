$$f'(x) = \sum_{k=2}^{\infty} m_k a_k x^{k-1} = a_1 + \sum_{k=2}^{\infty} m_k a_k x^{k-1}$$

$$= a_1 + \sum_{k=2}^{\infty} (a_{k-1} - 2a_k) x^{k-1} = a_1 + \sum_{k=2}^{\infty} a_{k-1} x^{k-1} - 2 \sum_{k=2}^{\infty} a_k x^{k-1}$$

$$= a_1 - f(x) + 2x \sum_{k=2}^{\infty} (a_k - 2a_{k-1}) x^{k-2} = a_1 - f(x) + 2x \sum_{k=2}^{\infty} a_k x^{k-2} - 2x \sum_{k=2}^{\infty} a_{k-1} x^{k-2}$$

$$= a_1 + a_0 - f(x) + 2x f'(x) + 2f(x).$$

However, since $a_1 = a_0$, we get $f(x) = (4x - 1)f(x) + 2x(1 - f(x))$, or yet,

$$(2x - 1)f(x) = (4x - 1)f(x) + 2x(1 - f(x)).$$

In order to integrate (i.e., to find the solutions of) the above differential equation, note first that $f$ is positive in some interval $(-r, r)$, for some $0 < r \leq \frac{1}{2}$ (this comes from the fact that $f(0) = a_0 > 0$ and $f$ is continuous, hence has the same sign as $f(0)$ in a suitable neighborhood of 0). Thus, for $|x| < r$ we can write

$$\frac{f'(x)}{f(x)} = \frac{4x - 1}{2x - 1} = -2 + \frac{1}{2x - 1}$$

and then, for $|x| < r \leq \frac{1}{2}$,

$$\log f(x) = \log f(0) + \int_0^x \left( \frac{4t - 1}{2t - 1} \right) dt = -2 \int_0^x \frac{1}{2t - 1} dt = -2x \log(1 - 2x).$$

Hence, for $|x| < r \leq \frac{1}{2}$ we have

$$f(x) = e^{x - 2x \log(1 - 2x)} = e^{x} (1 - 2x)^{-2x}.$$

(3.13)

Step III — firstly, recall that the power series expansion of $e^{-2x}$ is given by letting $z = -2$ in (3.8), and is valid in the whole real line:

$$e^{-2x} = \sum_{k=0}^{\infty} \frac{(-2x)^k}{k!} = \sum_{k=0}^{\infty} \frac{(-1)^k 2^k x^k}{k!}.$$
