from typing import Dict, List
from entity import Linear, Point, PointAspect, Route, Signal


def parse_route(system, data, extras_data, point_data):
    blocks = extras_data.get('blocks', []) or []
    platforms = extras_data.get('platforms', []) or []
    crossings = extras_data.get('crossings', []) or []

    seg_ngh: Dict[str, List[str]] = {}
    sig_ngh: Dict[str, List[str]] = {}

    sections: Dict[str, Linear] = {}
    points: Dict[str, Point] = {}
    signals: Dict[str, Signal] = {}

    table = data.get('interlocking-table', [])
    point_config = point_data.get('points', [])

    # Parse block segments and signals neighbors
    def parse_segment(item):
        sid = item['id']

        if not sid:
            return

        main = item['main'][0]
        overlaps = item['overlaps'] if item.get('overlaps') is not None else []

        if main not in seg_ngh:
            if not len(overlaps):
                seg_ngh[main] = [main]
            else:
                seg_ngh[main] = overlaps

        sigs = item['signals'] if item.get('signals') is not None else []

        if len(sigs):
            if item.get('overlaps') is not None:
                for i, val in enumerate(overlaps):
                    if val not in sig_ngh:
                        if i%2 == 0:
                            sig_ngh[val] = {'down': sigs[i]}
                        else:
                            sig_ngh[val] = {'up': sigs[i]}

            else:
                sig_ngh[main] = {'down': sigs[0]}

    for b in blocks:
        if isinstance(b, dict):
            parse_segment(b)

    for p in platforms:
        if isinstance(p, dict):
            parse_segment(p)

    for c in crossings:
        if not isinstance(c, dict):
            continue

        sid = c.get('id')

        if not sid:
            continue

        seg = c.get('segment')
        seg_ngh[f"{sid}.line1"] = [seg]
        seg_ngh[f"{sid}.line2"] = [seg]
        sig_ngh.setdefault(sid, [])

    # Create signals/sections/points from the table
    for entry in table:
        # Table Signals
        e_signals = entry.get('signals', [])

        if e_signals is not None:
            for s in e_signals:
                sid = s.get('id')

                if sid and sid not in signals:
                    signals[sid] = Signal(name=sid)

        # Source/destination signals (route entry and exit signals)
        src_id = entry.get('source')
        dst_id = entry.get('destination')

        if src_id and src_id not in signals:
            signals[src_id] = Signal(name=src_id)

        if dst_id and dst_id not in signals:
            signals[dst_id] = Signal(name=dst_id)

        # Table Points
        e_points = entry.get('points', [])

        if e_points is not None:
            for pt in e_points:
                pid = pt.get('id')

                if pid is not None:
                    for pc in point_config: # point neighbors
                        pc_seg = pc.get('seg')
                        pc_stem = pc.get('stem')
                        pc_normal = pc.get('normal')
                        pc_reverse = pc.get('reverse')

                        if pid == pc.get('id') and pid not in points:
                            points[pid] = Point(
                                name=pid,
                                segName=pc_seg,
                                stem_neighbor=pc_stem,
                                normal_neighbor=pc_normal,
                                reverse_neighbor=pc_reverse
                            )
    
    for entry in table:
        path = entry.get('path', [])
        dirc = 'up' if entry.get('orientation') == 'anticlockwise' else 'down'
        src = entry.get('source', [])
        dst = entry.get('destination', [])
        first = path[0]
        last = path[-1]

        # Table Path Elements
        p_seg_names = [pnt.segName for pnt in points.values()]

        for i, p in enumerate(path):
            sid = p.get('id')

            if sid and sid not in p_seg_names:
                if sid in signals: # Segment signal neighbors
                    seg_n = path[i-1]["id"] if i > 0 else None

                    if seg_n and seg_n in sections:
                        if dirc == 'up':
                            sections[seg_n].up_signal = signals[sid]
                        else:
                            sections[seg_n].down_signal = signals[sid]

                else: # Segment end neighbors
                    if sid not in sections:
                        sections[sid] = Linear(name=sid)

                    seg_down: str = None
                    seg_up: str = None
                    sn_data = seg_ngh.get(sid)

                    if sn_data and len(sn_data) > 1:
                        seg_down = sn_data[0]
                        seg_up = sn_data[1]
                    else:
                        seg_down = path[i-1]['id'] if (i-1)>=0 and path[i-1] is not None else None
                        seg_up = path[i+1]['id'] if (i+1)<len(path) and path[i+1] is not None else None

                        if dirc == 'down':
                            seg_up, seg_down = seg_down, seg_up

                    if sid in sections:
                        if seg_up is not None:
                            sections[sid].up_neighbor = seg_up

                        if seg_down is not None:
                            sections[sid].down_neighbor = seg_down

                        if sid in sig_ngh:
                            for k, val in sig_ngh.get(sid).items():
                                if k == 'up':
                                    sections[sid].up_signal = val
                                elif k == 'down':
                                    sections[sid].down_signal = val
        
        """
        Configure remaining possible neighbors association for section's end segment
        with accordance of their entry/exit signals which specifies the source of a route.
        """
        for sec in sections.values():
            ng_sig = sec.up_signal if dirc == 'up' else sec.down_signal
            ng_sig_name = ng_sig.name if isinstance(ng_sig, Signal) else ng_sig

            if ng_sig_name == src:
                if first:
                    first_elem = None

                    if first['id'] in sections:
                        first_elem = sections[first['id']]
                    else:
                        for pnt_id, pnt_val in points.items():
                            if first['id'] == pnt_val.segName:
                                first_elem = points[pnt_id]
                                break

                    if first_elem is not None:
                        if dirc == 'up':
                            if isinstance(first_elem, Linear) and first_elem.down_neighbor is None:
                                first_elem.down_neighbor = sec

                            if sec.up_neighbor is None:
                                sec.up_neighbor = first_elem
                        elif dirc == 'down':
                            if isinstance(first_elem, Linear) and first_elem.up_neighbor is None:
                                first_elem.up_neighbor = sec

                            if sec.down_neighbor is None:
                                sec.down_neighbor = first_elem

        # Instantiate segment neighbors Section and Signal
        for sec in sections.values():
            down_ngh = sec.down_neighbor
            up_ngh = sec.up_neighbor

            if not isinstance(down_ngh, Linear) and down_ngh in sections:
                sec.down_neighbor = sections[down_ngh]
            elif not isinstance(down_ngh, Point):
                for i, val in points.items():
                    if down_ngh and down_ngh == val.segName:
                        sec.down_neighbor = points[i]
            
            if not isinstance(up_ngh, Linear) and up_ngh in sections:
                sec.up_neighbor = sections[up_ngh]
            elif not isinstance(up_ngh, Point):
                for i, val in points.items():
                    if up_ngh and up_ngh == val.segName:
                        sec.up_neighbor = points[i]

            down_sig = sec.down_signal
            up_sig = sec.up_signal

            if not isinstance(down_sig, Signal):
                if down_sig is not None and down_sig in signals:
                    sec.down_signal = signals[down_sig]
            
            if not isinstance(up_sig, Signal):
                if up_sig is not None and up_sig in signals:
                    sec.up_signal = signals[up_sig]

        # Instantiate point neighbors Section
        for pnt in points.values():
            p_stem = pnt.stem_neighbor
            p_normal = pnt.normal_neighbor
            p_reverse = pnt.reverse_neighbor

            if p_stem is not None:
                if not isinstance(p_stem, Point) and p_stem in points:
                    pnt.stem_neighbor = points[p_stem]
                elif not isinstance(p_stem, Linear) and p_stem in sections:
                    pnt.stem_neighbor = sections[p_stem]
            
            if p_normal is not None:
                if not isinstance(p_normal, Point) and p_normal in points:
                    pnt.normal_neighbor = points[p_normal]
                elif not isinstance(p_normal, Linear) and p_normal in sections:
                    pnt.normal_neighbor = sections[p_normal]
            
            if p_reverse is not None:
                if not isinstance(p_reverse, Point) and p_reverse in points:
                    pnt.reverse_neighbor = points[p_reverse]
                elif not isinstance(p_reverse, Linear) and p_reverse in sections:
                    pnt.reverse_neighbor = sections[p_reverse]

    # Resolve string neighbors that are signal names (signal-in-path segments)
    for sec in sections.values():
        if isinstance(sec.up_neighbor, str) and sec.up_neighbor in signals:
            sec.up_signal = signals[sec.up_neighbor]
            sec.up_neighbor = None

        if isinstance(sec.down_neighbor, str) and sec.down_neighbor in signals:
            sec.down_signal = signals[sec.down_neighbor]
            sec.down_neighbor = None

    # Add to the interlocking system
    for pt in points.values():
        system.add_section(pt)

    for sec in sections.values():
        system.add_section(sec)

    for sig in signals.values():
        system.add_signal(sig)

    # Build Routes
    id_to_route = {}

    for entry in table:
        rid = entry.get('id')
        rname = f"r{rid}"
        source = entry.get('source')
        destination = entry.get('destination')
        dir = entry.get('orientation')

        if dir == 'anticlockwise':
            direction = 'up'
        else:
            direction = 'down'

        # Append segments and points in the path
        path_list = []

        for p in entry.get('path', []):
            sid = p.get('id')
            if sid in sections:
                path_list.append(sections[sid])
            else:
                for pnt, val in points.items():
                    if sid == val.segName:
                        path_list.append(points[pnt])

        # Append points' configured aspect
        pts = {}
        e_pnt = entry.get('points', [])

        if e_pnt is not None:
            for pt in e_pnt:
                pid = pt.get('id')
                pos = pt.get('position', 'normal').upper()

                if pid in points:
                    asp = PointAspect.NORMAL if pos == 'NORMAL' else PointAspect.REVERSE
                    pts[points[pid]] = asp

        # Append signals
        sig_objs = [signals[s.get('id')] for s in entry.get('signals', []) if s.get('id') in signals]

        # Create route
        route = Route(
            name=rname,
            path=path_list,
            overlap=[],
            points=pts,
            signals=sig_objs,
            entry_signal=signals.get(source),
            exit_signal=signals.get(destination),
            entry_dir=direction
        )
        id_to_route[rid] = route

        # Add the route to the interlocking system
        system.add_route(route)

    # Link conflicts
    for entry in table:
        rid = entry.get('id')
        route = id_to_route.get(rid)
        e_conf = entry.get('conflicts', [])

        if e_conf is not None:
            for c in e_conf:
                cid = c.get('id')
                if cid in id_to_route:
                    route.conflicts.add(id_to_route[cid])
