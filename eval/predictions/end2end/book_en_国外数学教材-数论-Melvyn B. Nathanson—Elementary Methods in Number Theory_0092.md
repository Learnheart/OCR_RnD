2.7 Public Key Cryptography 79

Theorem 2.19 Let $m$ be an integer that is the product of two prime numbers. The prime divisors of $m$ are the roots of the quadratic equation

$$x^2 - (m + 1 - \nu(m))x + m = 0,$$

and so $\nu(m)$ determines the prime factors of $m$.

Proof. If $m = p q$, then

$$\nu(m) = (p - 1)(q - 1) = m - p - q + 1 = m - p - q + 1,$$

and so

$$p - (m + 1 - \nu(m)) = \frac{m}{q}.$$

Equivalently, $p$ and $q$ are the solutions of the quadratic equation

$$x^2 - (m + 1 - \nu(m))x + m = 0.$$

This completes the proof. $\square$

For example, if $m = 221$ and $\nu(m) = 192$, then the quadratic equation

$$x^2 - 30x + 221 = 0$$

has solutions $x = 13$ and $x = 17$, and thus $m = 13 \cdot 17$.

This method, known as the RSA cryptosystem, is called a public key cryptosystem, since the encryption key is made available to everyone, and the encrypted message can be transmitted through public channels. Only the possessor of the prime factors of $m$ can decrypt the message. RSA is simple, but useful, and is the basis of many commercially valuable cryptosystems.

Exercises

1. Consider the secret key cryptosystem constructed from the prime $p = 947$ and the encoding key $e = 167$. Decipher the plaintext $P = 2$.

2. Find a decrypting key and decipher the ciphertext $C = 3$.

3. Consider the primes $p = 53$ and $q = 61$. Let $m = p q$. Prove that $e = 7$ is relatively prime to $\nu(m)$. Find a positive integer $d$ such that $ed \equiv 1 \pmod{\nu(m)}$.

4. The integer 6059 is the product of two distinct primes, and $\nu(6059) = 5904$. Use Theorem 2.19 to compute the prime divisors of 6059.

5. The probability that an integer chosen at random between 1 and $n$ is relatively prime to $n$ is $\frac{\nu(n)}{n}$. Let $x = p q$, where $p$ and $q$ are distinct primes greater than $x$. Prove that the probability that a randomly chosen positive integer up to $x$ is relatively prime to $n$ is greater than $(1 - 1/e)^2$. If $x = 200$, this probability is greater than 0.99.
