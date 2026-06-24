import argparse
import os
import sys
import textwrap

try:
    import yaml
except Exception:
    yaml = None

from parser import parse_route

from generator import generate_from_system
from interlocking import InterlockingSystem

if __name__ == '__main__':
    class ConfigAction(argparse.Action):
        def __init__(self, option_strings, dest, nargs=None, **kwargs):
            if nargs is not None:
                raise ValueError("nargs not allowed")
            super().__init__(option_strings, dest, **kwargs)
        def __call__(self, parser, namespace, values, option_string=None):
            joined_val = os.path.join('configs', values)
            setattr(namespace, self.dest, joined_val)

    parser = argparse.ArgumentParser(
        prog='app/main.py',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        description=textwrap.dedent('''\
                                    SWTbahn-Lite: Formal model generator
                                    ------------------------------------------------------
                                    Generates NuXmv model from interlocking configuration:
                                        --config-dir LAYOUT --out path_for_generated_model
                                    ''')
    )

    parser.add_argument('-c', '--config-dir', required=True,
                        action=ConfigAction,
                        default=os.path.join('configs'),
                        choices=['1_Straight', '2_Point', '3_Cross', '4_Mini', '5_Fork', '6_Twist', '7_Lite', 'Full'],
                        help='path to the network layout dir'
                        )
    
    parser.add_argument('--out', default=None, help='output file path (defaults to stdout)')
    parser.add_argument('--seg-up', type=int, default=None, metavar='INT',
                        help='segment ID whose occUp is initialised to COMPLETETRAINOCC')
    parser.add_argument('--seg-down', type=int, default=None, metavar='INT',
                        help='segment ID whose occDown is initialised to COMPLETETRAINOCC')

    args = parser.parse_args()
    system = InterlockingSystem()

    # Try to parse YAML interlocking table
    table_path = os.path.join(args.config_dir, 'interlocking_table.yml')
    extras_path = os.path.join(args.config_dir, 'extras_config.yml')
    point_config_path = os.path.join(args.config_dir, '../point_config.yml')

    if yaml is None:
        print('PyYAML is required to parse config files. Install with: pip install pyyaml', file=sys.stderr)
    
    if os.path.exists(table_path):
        if yaml is not None:
            with open(table_path, 'r') as fh:
                data = yaml.safe_load(fh)
        
        # Load point configuration
        if os.path.exists(point_config_path):
            if yaml is not None:
                with open(point_config_path, 'r') as fh:
                    point_data = yaml.safe_load(fh)

        # Load extra specification
        if os.path.exists(extras_path):
            if yaml is not None:
                with open(extras_path, 'r') as fh:
                    extras_data = yaml.safe_load(fh)

        parse_route(system, data, extras_data, point_data)

    else:
        # Fallback: create small example as before
        from entity import Direction, ElementMode, ElementOcc
        from entity import Linear as L
        from entity import Point as P
        from entity import PointAspect
        from entity import Route as R
        from entity import Signal as S

        s1 = L(name='seg1')
        s2 = L(name='seg2')
        s3 = L(name='seg3')
        s4 = L(name='seg4')
        p1 = P(name='point1')
        sig1 = S(name='signal1')
        sig2 = S(name='signal2')
        sig3 = S(name='signal3')

        s1.up_neighbor = s2
        s2.down_neighbor = s1
        s2.up_neighbor = p1
        p1.stem_neighbor = s2
        p1.normal_neighbor = s3
        p1.reverse_neighbor = s4
        s3.down_neighbor = p1
        s4.down_neighbor = p1

        for sec in (s1, s2, s3, s4, p1):
            system.add_section(sec)

        for sig in (sig1, sig2, sig3):
            system.add_signal(sig)

        route1 = R(
            name='r1',
            path=[s1, s2, p1, s3],
            overlap=[],
            points={p1: PointAspect.NORMAL},
            signals=[sig1, sig2, sig3],
            entry_signal=sig1,
            exit_signal=sig2,
            entry_dir=Direction.DOWN
        )

        system.add_route(route1)
        
        first = route1.path[0]
        
        if isinstance(first, L):
            first.occDown = ElementOcc.HEADOCC
            first.MODE = ElementMode.USED
        
    # output
    if args.out:
        with open(args.out, 'w') as fh:
            generate_from_system(system, out=fh, seg_up=args.seg_up, seg_down=args.seg_down)
            print(f"SMV model generated - {args.out}")
    else:
        generate_from_system(system, seg_up=args.seg_up, seg_down=args.seg_down)
