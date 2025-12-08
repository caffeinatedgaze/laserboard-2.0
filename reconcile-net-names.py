from dataclasses import dataclass
import re

import pcbnew

board = pcbnew.GetBoard()

@dataclass(frozen=True)
class Group:
    # FOOTPRINT LD37
    # FOOTPRINT R76
    # FOOTPRINT R77
    # FOOTPRINT Q37
    laser: pcbnew.BOARD_ITEM
    resistor10k: pcbnew.BOARD_ITEM
    resistor220: pcbnew.BOARD_ITEM
    mosfet: pcbnew.BOARD_ITEM


def ensure_net(net_name: str) -> pcbnew.NETINFO_ITEM:
    """Fetch an existing net or create it if missing."""
    nets = board.GetNetsByName()
    netinfo = nets.get(net_name) if hasattr(nets, "get") else None
    if netinfo is None:
        try:
            netinfo = nets[net_name]
        except Exception:
            netinfo = None

    if netinfo is None:
        netinfo = pcbnew.NETINFO_ITEM(board, net_name)
        board.Add(netinfo)

    return netinfo


def process_pads(group, net_number):
    for pad in group.Pads():
        pname = pad.GetName() if hasattr(pad, "GetName") else ""
        netname = ""
        if hasattr(pad, "GetNetname"):
            netname = pad.GetNetname()
        elif hasattr(pad, "GetNet") and pad.GetNet() is not None:
            netname = pad.GetNet().GetNetname()
        if not netname:
            continue
        updated_netname = re.sub(r"\d+", net_number, netname)
        if updated_netname != netname:
            netinfo = ensure_net(updated_netname)
            if hasattr(pad, "SetNet"):
                pad.SetNet(netinfo)
            if hasattr(netinfo, "GetNet") and hasattr(pad, "SetNetCode"):
                pad.SetNetCode(netinfo.GetNet())
            print(f"      Pad: {pname or '?'} -> {netname} => {updated_netname}")
        else:
            print(f"      Pad: {pname or '?'} -> {netname}")


def build_group(items) -> Group:
    """Assign group members based on their reference designator prefix."""
    members = {}
    for it in items:
        ref = it.GetReference() if hasattr(it, "GetReference") else ""
        if not ref:
            continue
        if ref.startswith("LD"):
            members["laser"] = it
        elif ref.startswith("Q"):
            members["mosfet"] = it
        elif ref.startswith("R"):
            slot = "resistor10k" if "resistor10k" not in members else "resistor220"
            members[slot] = it

    missing = {"laser", "resistor10k", "resistor220", "mosfet"} - set(members)
    if missing:
        raise RuntimeError(f"Group missing expected members: {sorted(missing)}")

    return Group(
        laser=members["laser"],
        resistor10k=members["resistor10k"],
        resistor220=members["resistor220"],
        mosfet=members["mosfet"],
    )

groups = []

for grp in board.Groups():          # GROUPS -> sequence of PCB_GROUP
    name = grp.GetName()
    items = grp.GetItems()          # container of BOARD_ITEM*
    print(f"Group: '{name}'  ({len(items)} items)")

    for it in items:
        t = type(it).__name__
        ref = it.GetReference() if hasattr(it, "GetReference") else ""
        print(f"   {t} {ref}")
    group_obj = build_group(items)
    groups.append(group_obj)

for group in groups:
    print(
        "mosfet reference", group.mosfet.GetReference()
    )
    required_net_number = group.mosfet.GetReference().replace("Q", "")
    process_pads(group.laser, required_net_number)
    process_pads(group.resistor10k, required_net_number)
    process_pads(group.resistor220, required_net_number)
    process_pads(group.mosfet, required_net_number)

print(f"   Built Group object: {group_obj}")
print()
