B4 For any continuous real-valued function $f$ defined on the interval $[0,1]$, let
$$
p(f) = \int_0^1 f(x) dx, \quad \text{Var}(f) = \int_0^1 \left(f(x) - p(f)\right)^2 dx,
$$
$$
M(f) = \max_{x \in [0,1]} |f(x)|.
$$
Show that if $f$ and $g$ are continuous real-valued functions defined on the interval $[0,1]$, then
$$
\text{Var}(f) \leq 2\text{Var}(f|M(f)|) + 2\text{Var}(g|M(g)|).
$$

B5 Let $X = \{1, 2, \ldots, n\}$, and let $k \geq 0$. Show that there are exactly $k \cdot 2^{n-k}$ functions $f: X \to X$ such that for every $x \in X$ there is a $j \geq 0$ such that $f^{(j)}(x) = x$ and $f^{(j)}(x) = f(f^{(j-1)}(x))$.

B6 Let $n \geq 1$ be an odd integer. Alice and Bob play the following game, taking alternating turns, with Alice playing first. The playing area consists of $n$ spaces, arranged in a line. Initially all spaces are empty. At each turn, a player either
- places a stone in an empty space, or
- removes a stone from a nonempty space $x$, places a stone in the nearest empty space to the left of $x$ (if such a space exists), and places a stone in the nearest empty space to the right of $x$ (if such a space exists).

Furthermore, a move is permitted only if the resulting position has not occurred previously in the game. A player loses if he or she is unable to move. Assuming that both players play optimally throughout the game, what moves may Alice make on her first turn?
