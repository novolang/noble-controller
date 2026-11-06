#!/usr/bin/env python3
"""Write the numbers of tests/ll_cs_vectors_tests.nv from the sample data of the Bluetooth Core Specification.

    python3 -I tests/cs_vectors.py CORE_TEXT [TEST_FILE]

CORE_TEXT is the text of Core 6.3 (one file, as `pdftotext -layout` writes it).  The script reads Volume 6 Part C, Section 8.1, Sets 1 to 4,
which show a procedure of Channel Selection Algorithm #3b step by step, and replaces the lines of TEST_FILE (default: tests/ll_cs_vectors_tests.nv
beside this script) between `// ---- generated data begin` and `// ---- generated data end` with the constants of the four sets.  The test file
holds the numbers and not the text: the specification is not needed to run the tests.

Each set gives, for every step of its procedures, the mode, the access addresses of both directions, the tone extension slots, the antenna path
permutation and the sounding sequence of each direction (the last as the markers and their positions, or as the bits themselves), and the
shuffled channel lists with the step they were made at.  Sets 1 to 3 give no channel for a step: the script takes it from the lists, with the
rules of Part H, Sections 4.1 and 4.2 (the next entry of the list of its kind; the channel of the main step before it for a sub step of mode 1;
the channel of a step of the subevent before for a repeated step), and stops when a list the sample makes is not made at the step that needs it.
Set 4 gives the channel, the start time and the repetition of every step, and its two accounts of each step (the log and the resulting
procedure) are held against each other.
"""
import os
import re
import sys

STRIDE = 18
NOISE = re.compile(r'^(Bluetooth SIG Proprietary|BLUETOOTH CORE SPECIFICATION|Sample Data\s*$)')
BEGIN = '// ---- generated data begin'
END = '// ---- generated data end'


def clean(lines):
    return [ln.rstrip() for ln in lines if not NOISE.match(ln.strip())]


def norm(s):
    return re.sub(r'\s+', ' ', s)


def hexbytes(s):
    return [int(x, 16) for x in re.findall(r'\b[0-9A-F]{2}\b', s)]


def find_sets(lines):
    """The line ranges of Sets 1 to 4 of Section 8.1: from the heading of each to the heading that follows."""
    heads = []
    for i, ln in enumerate(lines):
        m = re.match(r'^8\.1\.([1-4])\s+Set [1-4]\s*$', ln)
        if m and i > 100000:
            heads.append((int(m.group(1)), i))
        m = re.match(r'^8\.2\s+Channel Selection Algorithm #3c', ln)
        if m and i > 100000:
            heads.append((0, i))
    heads = sorted(heads, key=lambda h: h[1])
    out = {}
    for (k, a), (_, b) in zip(heads, heads[1:]):
        if k:
            out[k] = (a, b)
    assert sorted(out) == [1, 2, 3, 4], 'the sets of Section 8.1 are not where the script expects them'
    return out


def parse_a(seg, k):
    """Sets 1 to 3: the T_ID format, one block of lines for each step."""
    seg = clean(seg)
    text = '\n'.join(seg)
    cfg = {}
    cfg['chm'] = [int(x, 16) for x in re.search(r'ChM = 0x([0-9A-F ]+)', text).group(1).split()][::-1]
    for key, pat in [('ch_rep', r'ChM_Repetition = (\d+)'), ('main', r'Main_Mode = 0x(\d+)'), ('sub', r'Sub_Mode = 0x(\d+)'),
                     ('min', r'Main_Mode_Min_Steps = (\d+)'), ('max', r'Main_Mode_Max_Steps = (\d+)'),
                     ('rep', r'Main_Mode_Repetition = (\d+)'), ('mode0', r'Mode_0_Steps = (\d+)'),
                     ('rtt', r'RTT_Type = 0x(\d+)'), ('aci', r'ACI = (\d+)'), ('procs', r'Procedure_Count = (\d+)')]:
        cfg[key] = int(re.search(pat, text).group(1))
    blocks = []
    proc = 0
    last = -1
    cur = None
    for ln in seg:
        m = re.match(r'^Step=(\d+) \| Mode=(\d+)', ln)
        if m:
            if cur is not None:
                blocks.append(cur)
            s = int(m.group(1))
            if s == 0 and last >= 0:
                proc += 1
            last = s
            cur = (proc, s, int(m.group(2)), [])
        elif cur is not None:
            cur[3].append(ln)
    blocks.append(cur)
    recs = []
    lists = []
    range_pat = r'-\s+Range\s*=\s*(\d+)\s*\(decimal\);\s*hr1\s*=\s*(\d+)'
    for proc, st, mode, lines in blocks:
        t = '\n'.join(lines)
        r = dict(proc=proc, step=st, mode=mode, rep=0, ch=-1, start=-1, aa_i=-1, aa_r=-1, ext_i=-1, ext_r=-1, perm=-1,
                 seq_i=[0, 0, 0, 0], seq_r=[0, 0, 0, 0])
        for m in re.finditer(r'T_ID (\d) -\s+Shuffled channels:\s*([0-9 \n]+?)(?=\n\s*\n|\n\*)', t):
            lists.append(dict(proc=proc, step=st, tid=int(m.group(1)), list=[int(x) for x in m.group(2).split()]))
        for who, key in (('Initiator', 'aa_i'), ('Reflector', 'aa_r')):
            m = re.search(who + r' chosen PN pattern:\s*((?:[0-9A-F]{2}\s+){3}[0-9A-F]{2})', t)
            if m:
                r[key] = int(''.join('%02X' % x for x in hexbytes(m.group(1))[:4]), 16)
        m = re.search(r'TPM extension \(\d ?bits\):\s*([0-9A-F]{2})', t)
        if m:
            v = int(m.group(1), 16)
            r['ext_i'] = (v >> 7) & 1
            r['ext_r'] = (v >> 6) & 1
        m = re.search(r'Antenna path perm\. \(\d+ ?bits\):\s*(?:[0-9A-F]{2}\s+)+' + range_pat, t)
        if m:
            r['perm'] = int(m.group(2))
        for who, key in (('initiator', 'seq_i'), ('reflector', 'seq_r')):
            pm = re.search(r'SS marker position ' + who + r' \(\d+ ?bits\):\s*(?:[0-9A-F]{2}\s+)+' + range_pat, t)
            sm = re.search(r'SS marker sig\. sel\. ' + who + r' \(\d ?bits\):\s*([0-9A-F]{2})', t)
            if not pm:
                continue
            assert pm.group(1) == '29', (k, st)
            pos = int(pm.group(2))
            sig = (int(sm.group(1), 16) >> 7) & 1
            bits = [n & 1 for n in range(32)]
            for j, v in enumerate([1, 1, 0, 0] if sig == 0 else [0, 0, 1, 1]):
                bits[pos + j] = v
            r[key] = [sum(bits[j] << j for j in range(32)), 0, 0, 0]
            m = re.search(who.capitalize() + r' Sounding Sequence:\s*([01 \n]+?)\(Tx', t)
            if m:
                assert re.sub(r'[^01]', '', m.group(1)) == ''.join(str(b) for b in bits), (k, st, who)
        if mode != 2:
            assert r['aa_i'] >= 0 and r['aa_r'] >= 0, (k, st)
        if mode >= 2:
            assert r['ext_i'] >= 0 and r['perm'] >= 0, (k, st)
        if mode in (1, 3):
            assert r['seq_i'][0] != 0 and r['seq_r'][0] != 0, (k, st)
        recs.append(r)
    return cfg, recs, lists


def channels(cfg, recs, lists):
    """The channel and the repetition of each step of Sets 1 to 3, and the steps of each subevent of each procedure."""
    subs = []
    for proc in sorted(set(r['proc'] for r in recs)):
        rs = [r for r in recs if r['proc'] == proc]
        l0 = [l for l in lists if l['proc'] == proc and l['tid'] == 1]
        ln = [l for l in lists if l['proc'] == proc and l['tid'] == 0]
        subevents = []
        idx = 0
        while idx < len(rs):
            sub = []
            for _ in range(cfg['mode0']):
                assert rs[idx]['mode'] == 0
                sub.append(rs[idx])
                idx += 1
            while idx < len(rs) and rs[idx]['mode'] != 0:
                sub.append(rs[idx])
                idx += 1
            subevents.append(sub)
        cur0, p0, curn, pn = None, 0, None, 0
        prev_main, last_main = [], None
        for sub in subevents:
            cur_main = []
            nrep = min(cfg['rep'], len(prev_main))
            rep_src = prev_main[len(prev_main) - nrep:] if nrep else []
            k = 0
            for r in sub:
                if r['mode'] == 0:
                    if cur0 is None or p0 >= len(cur0):
                        nxt = l0.pop(0)
                        assert nxt['step'] == r['step'], 'the mode 0 list is not made at the step that needs it'
                        cur0, p0 = nxt['list'], 0
                    r['ch'] = cur0[p0]
                    p0 += 1
                    continue
                if k < nrep:
                    r['ch'], r['rep'] = rep_src[k], 1
                    k += 1
                    continue
                is_sub = cfg['sub'] != 0 and r['mode'] == cfg['sub']
                if is_sub and cfg['sub'] == 1:
                    r['ch'] = last_main
                    continue
                if curn is None or pn >= len(curn):
                    nxt = ln.pop(0)
                    assert nxt['step'] == r['step'], 'the list is not made at the step that needs it'
                    curn, pn = nxt['list'], 0
                r['ch'] = curn[pn]
                pn += 1
                if not is_sub:
                    last_main = r['ch']
                    cur_main.append(r['ch'])
            prev_main = cur_main
        subs += [len(s) for s in subevents] + [0]
    return subs


def parse_b(seg):
    """Set 4: the log of the draws and the resulting procedure."""
    text = '\n'.join(clean(seg))
    i = text.index('Resulting Procedure')
    log, res = norm(text[:i]), norm(text[i:])
    aa = {int(m.group(1)): (int(m.group(2), 16), int(m.group(3), 16))
          for m in re.finditer(r'AA generation, CSStepCount (\d+)\. AA_I 0x([0-9A-F]{8}), AA_R 0x([0-9A-F]{8})', log)}
    ext = {int(m.group(3)): (int(m.group(1)), int(m.group(2)))
           for m in re.finditer(r'Tone extensions: I (\d), R (\d)\. CSStepCount (\d+)', log)}
    perm = {int(m.group(3)): int(m.group(1))
            for m in re.finditer(r'Antenna Path Permutation Index: (\d+)\. N_AP = (\d), CSStepCount (\d+)', log)}
    starts = [(int(m.group(2)), 1 if m.group(3) == 'Mode-0' else 0, int(m.group(1)))
              for m in re.finditer(r'cr1 start\. nChannels (\d+), CSStepCount (\d+), (Mode-0|Non-Mode-0)', log)]
    ends = [[int(x) for x in m.group(1).split()] for m in re.finditer(r'cr1 end\. channels ((?:\d+ )+)', log + ' ')]
    assert len(starts) == len(ends)
    lists = []
    for (st, tid, n), lst in zip(starts, ends):
        assert len(lst) == n
        lists.append(dict(proc=0, step=st, tid=tid, list=lst))
    d = res[res.index('Detail'):]
    parts = re.split(r'Step # ?(\d+):', d)
    recs = []
    for j in range(1, len(parts), 2):
        n, t = int(parts[j]), parts[j + 1]
        m = re.match(r' (Main-Mode Repetition, )?Mode-(\d) step on ch (\d+), \+([0-9.]+) (µs|ms) after subevent anchor', t)
        mode = int(m.group(2))
        r = dict(proc=0, step=n, mode=mode, rep=1 if m.group(1) else 0, ch=int(m.group(3)),
                 start=int(round(float(m.group(4)) * (1000 if m.group(5) == 'µs' else 1000000))),
                 aa_i=-1, aa_r=-1, ext_i=-1, ext_r=-1, perm=-1, seq_i=[0, 0, 0, 0], seq_r=[0, 0, 0, 0])
        for who, key in (('Initiator', 'aa_i'), ('Reflector', 'aa_r')):
            m = re.search(who + r' (?:Sync AA only|\d+-bit sounding sequence), AA 0x([0-9A-F]{8})', t)
            if m:
                r[key] = int(m.group(1), 16)
        if mode >= 2:
            mi = re.search(r'Initiator (\d+) µs tone[^=]*= APPI (\d+)(, tone extension present)?', t)
            mr = re.search(r'Reflector (\d+) µs tone[^=]*= APPI (\d+)(, tone extension present)?', t)
            assert mi.group(2) == mr.group(2)
            r['perm'] = int(mi.group(2))
            r['ext_i'] = 1 if mi.group(3) else 0
            r['ext_r'] = 1 if mr.group(3) else 0
        for who, key in (('Initiator', 'seq_i'), ('Reflector', 'seq_r')):
            m = re.search(who + r' (\d+)-bit sounding sequence, AA .*?Bits ((?:\d+: \{[01]{8}\} ?)+)', t)
            if m:
                bits = ''
                for mm in re.finditer(r'(\d+): \{([01]{8})\}', m.group(2)):
                    assert int(mm.group(1)) == len(bits) // 8
                    bits += mm.group(2)
                assert len(bits) == int(m.group(1))
                words = [0, 0, 0, 0]
                for q, c in enumerate(bits):
                    if c == '1':
                        words[q // 32] |= 1 << (q % 32)
                r[key] = words
        recs.append(r)
    for r in recs:
        n = r['step']
        if r['mode'] != 2:
            assert aa[n] == (r['aa_i'], r['aa_r']), n
        if r['mode'] >= 2:
            assert ext[n] == (r['ext_i'], r['ext_r']) and perm[n] == r['perm'], n
    subevents = []
    for m in re.finditer(r'SubEvent (\d+), ([0-9.]+) (ns|µs|ms)[–-]([0-9.]+ (?:ns|µs|ms)), steps (\d+)–(\d+)', res[:res.index('Detail')]):
        anchor = int(round(float(m.group(2)) * {'ns': 1, 'µs': 1000, 'ms': 1000000}[m.group(3)]))
        subevents.append((anchor, int(m.group(6)) - int(m.group(5)) + 1))
    return recs, lists, subevents


def row(r):
    return [r['step'], r['mode'], r['rep'], r['ch'], r['start'], r['aa_i'], r['aa_r'], r['ext_i'], r['ext_r'], r['perm']] + r['seq_i'] + r['seq_r']


def fmt(name, ints, per):
    lines = ['const %s = [' % name]
    for i in range(0, len(ints), per):
        lines.append('    ' + ', '.join(str(v) for v in ints[i:i + per]) + ',')
    lines[-1] = lines[-1].rstrip(',') + ']'
    return '\n'.join(lines)


def data(core_lines):
    sets = find_sets(core_lines)
    out = []
    for k in (1, 2, 3):
        cfg, recs, lists = parse_a(core_lines[sets[k][0]:sets[k][1]], k)
        subs = channels(cfg, recs, lists)
        cfgv = [cfg['ch_rep'], cfg['main'], cfg['sub'], cfg['min'], cfg['max'], cfg['rep'], cfg['mode0'], 1, cfg['rtt'], cfg['aci'], cfg['procs'],
                1000000, 145, 145, 150, 40, 0] + cfg['chm']
        out.append(fmt('S%d_CFG' % k, cfgv, 27))
        out.append(fmt('S%d_SUBS' % k, subs, 16))
        out.append(fmt('S%d_STEPS' % k, [v for r in recs for v in row(r)], STRIDE))
        out.append(fmt('S%d_LISTS' % k, [v for l in lists for v in [l['proc'], l['step'], l['tid'], len(l['list'])] + l['list']], 20))
    recs, lists, subevents = parse_b(core_lines[sets[4][0]:sets[4][1]])
    seg = '\n'.join(core_lines[sets[4][0]:sets[4][1]])
    chm = [int(x, 16) for x in re.search(r'ChM = 0x([0-9A-F ]+)', seg).group(1).split()][::-1]
    cfgv = [2, 3, 2, 1, 6, 2, 1, 2, 2, 7, 1, 4000, 145, 145, 150, 10, 10] + chm
    out.append(fmt('S4_CFG', cfgv, 27))
    out.append(fmt('S4_SUBS', [n for _, n in subevents] + [0], 16))
    out.append(fmt('S4_STEPS', [v for r in recs for v in row(r)], STRIDE))
    out.append(fmt('S4_LISTS', [v for l in lists for v in [l['proc'], l['step'], l['tid'], len(l['list'])] + l['list']], 20))
    out.append(fmt('S4_ANCHORS', [a for a, _ in subevents], 10))
    return '\n'.join(out) + '\n'


def main():
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    core = open(sys.argv[1], encoding='utf-8').read().split('\n')
    here = os.path.dirname(os.path.abspath(__file__))
    path = sys.argv[2] if len(sys.argv) > 2 else os.path.join(here, 'll_cs_vectors_tests.nv')
    src = open(path, encoding='utf-8').read()
    a, b = src.index(BEGIN) + len(BEGIN) + 1, src.index(END)
    text = src[:a] + data(core) + src[b:]
    open(path, 'w', encoding='utf-8').write(text)


main()
