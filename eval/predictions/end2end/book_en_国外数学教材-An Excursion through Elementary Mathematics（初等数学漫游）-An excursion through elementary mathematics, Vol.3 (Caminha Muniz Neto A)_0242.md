236
9 Calculus and Number Theory

Proof. Firstly, from (9.14) we get
$$
\left| \rho_k - \sum_{k=1}^n \frac{\mu(k)}{k^2} \right| = \left| \sum_{k=1}^n \mu(k) \left( \frac{1}{k^2} - \frac{1}{k^2} \right) \right|
$$
(9.15)
$$
\leq \sum_{k=1}^n \left| \frac{1}{k^2} - \frac{1}{k^2} \right| = \frac{2}{n} \sum_{k=1}^n \frac{1}{k}.
$$

In order to estimate the last sum above, we claim that, given natural numbers $n$ and $k$ such that $1 \leq k \leq n$, we have
$$
\left| \frac{1}{k^2} - \frac{1}{k^2} \right| < \frac{2}{nk}.
$$

Indeed,
$$
\frac{n}{k} - 1 < \left( \frac{n}{k} \right)^2 \leq \frac{n^2}{k^2} \Rightarrow \frac{2n}{k^2} - \frac{1}{k^2} < \frac{n^2}{k^2} \Rightarrow \frac{1}{k^2} - \frac{1}{k^2} < \frac{1}{k^2}
$$
$$
\Rightarrow \frac{1}{k^2} - \frac{1}{k^2} < \frac{1}{k^2} \leq \frac{1}{k^2}
$$
$$
\Rightarrow 0 \leq \frac{1}{k^2} - \frac{1}{k^2} < \frac{2}{nk}.
$$

as wished.

Back to (9.15), we obtain from the above estimates that
$$
\left| \rho_k - \sum_{k=1}^n \frac{\mu(k)}{k^2} \right| < \sum_{k=1}^n \left( \frac{2}{k^2} - \frac{1}{k^2} \right) = \frac{2}{n} \sum_{k=1}^n \frac{1}{k} - 1.
$$

Now, from L’Hôpital’s rule we get
$$
\frac{2}{n} \sum_{k=1}^n \frac{1}{k} - 2 \left( 1 + \int_0^1 \frac{1}{x} dx \right) = \frac{2}{n} \sum_{k=1}^n \frac{1}{k} - 2 \log(n+1) \to 0
$$

as $n \to +\infty$. Hence,
$$
\lim_{n \to +\infty} \left( \frac{2}{n} \sum_{k=1}^n \frac{1}{k} - 1 \right) = 0,
$$

and our previous estimates assure that
