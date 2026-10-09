from dataclasses import dataclass


@dataclass(frozen=True)
class AllowedDemoTarget:
    service: str
    port: int


TARGETS = {
    "web": AllowedDemoTarget("web", 5001),
    "api": AllowedDemoTarget("api", 5002),
    "worker": AllowedDemoTarget("worker", 5003),
}


def parse_target(value: str) -> AllowedDemoTarget:
    service, separator, port_text = value.partition(":")
    if not separator or service not in TARGETS or not port_text.isdecimal():
        raise ValueError("target must be an allowlisted service:port")
    target = TARGETS[service]
    if int(port_text) != target.port:
        raise ValueError("target must be an allowlisted service:port")
    return target
