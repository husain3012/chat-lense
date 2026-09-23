"""Fit a contiguous prefix in logarithmic encodes, never sample or skip rows."""

import json
from app.synthesis.packet import compact_packet
from app.synthesis.gemini import ProviderError


def fit_passage(packet, offset, processed, budget):
    samples = packet["samples"]
    # If long messages make the overlap itself too large, discard oldest overlap
    # only. All previously unprocessed messages must remain in their original order.
    while True:
        overlap = max(0, processed - offset)
        minimum = min(len(samples), overlap + 1)

        def size(count):
            return len(
                json.dumps(
                    compact_packet({**packet, "samples": samples[:count]})[0],
                    ensure_ascii=False,
                    separators=(",", ":"),
                ).encode()
            )

        if size(minimum) <= budget:
            break
        if overlap:
            samples = samples[1:]
            offset += 1
        else:
            raise ProviderError(
                "A message cannot fit the input budget. Increase it in Settings."
            )
    low, high = minimum, len(samples)
    while low < high:
        middle = (low + high + 1) // 2
        if size(middle) <= budget:
            low = middle
        else:
            high = middle - 1
    packet["samples"] = samples[:low]
    packet["coverage"]["sampled_messages"] = low
    return packet, offset
