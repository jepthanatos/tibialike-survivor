import heapq

DIRS_4 = [(0, 1), (0, -1), (1, 0), (-1, 0)]

def astar(world, sc, sr, gc, gr, max_nodes=380):
    """
    A* on the tile grid from (sc,sr) to (gc,gr).
    Returns list of (col,row) excluding the start tile.
    Returns [] if no path found or already at goal.
    """
    if (sc, sr) == (gc, gr):
        return []

    # Validar que el start sea alcanzable
    if not world.is_walkable(sc, sr):
        return []

    # If goal is impassable, find nearest walkable neighbour
    if not world.is_walkable(gc, gr):
        for dc, dr in DIRS_4:
            nc, nr = gc+dc, gr+dr
            if world.is_walkable(nc, nr):
                gc, gr = nc, nr
                break
        else:
            return []

    open_heap = [(0.0, (sc, sr))]
    came_from = {(sc, sr): None}
    g_score   = {(sc, sr): 0.0}
    visited   = 0

    while open_heap:
        visited += 1
        if visited > max_nodes:
            break

        _, cur = heapq.heappop(open_heap)

        if cur == (gc, gr):
            path = []
            while cur is not None:
                path.append(cur)
                cur = came_from[cur]
            path.reverse()
            return path[1:]   # exclude start

        cc, cr = cur
        for dc, dr in DIRS_4:
            nb = (cc+dc, cr+dr)
            if not world.is_walkable(nb[0], nb[1]):
                continue
            new_g = g_score[cur] + 1.0
            if nb not in g_score or new_g < g_score[nb]:
                g_score[nb] = new_g
                f = new_g + abs(nb[0]-gc) + abs(nb[1]-gr)
                heapq.heappush(open_heap, (f, nb))
                came_from[nb] = cur

    return []
