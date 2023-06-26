# BSD 3-Clause License

# Copyright (c) 2023, AUTHORS
# All rights reserved.

# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:

# 1. Redistributions of source code must retain the above copyright notice, this
#    list of conditions and the following disclaimer.

# 2. Redistributions in binary form must reproduce the above copyright notice,
#    this list of conditions and the following disclaimer in the documentation
#    and/or other materials provided with the distribution.

# 3. Neither the name of the copyright holder nor the names of its
#    contributors may be used to endorse or promote products derived from
#    this software without specific prior written permission.

# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
# DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE
# FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL
# DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR
# SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER
# CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY,
# OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

"""Helpers for testing."""

from typing import Any, List
import pandas as pd


def get_trivial_sample_dataframe() -> pd.DataFrame:
    """Returns a trivial sample dataframe.

    The text in this sample was auto generated by Github Copilot. I started it
    with "In this work we perform science." and then kept pressing tab to see
    what it would generate. I added the "We used the Really Great Dataset for our
    analysis in this work." to have something to find.
    """
    return pd.DataFrame(
        {
            "text": [
                (
                    "In this work we perform science. The kind of science that "
                    "discovers things. We also perform art. The kind of art that "
                    "creates things. We also perform engineering. The kind of "
                    "engineering that builds things. We also perform business. "
                    "The kind of business that sells things. We also perform "
                    "medicine. The kind of medicine that heals things. We also "
                    "perform law. The kind of law that regulates things. We also "
                    "perform education. The kind of education that teaches things. "
                    "We also perform entertainment. The kind of entertainment that "
                    "entertains things. We also perform government. The kind of "
                    "government that governs things. We also perform religion. "
                    "The kind of religion that worships things. We also perform "
                    "sports. The kind of sports that plays things. We also perform "
                    "agriculture. The kind of agriculture that grows things. We "
                    "also perform military. The kind of military that fights things. "
                    "We also perform transportation. The kind of transportation "
                    "that transports things. We also perform communication. The "
                    "kind of communication that communicates things. We also "
                    "perform construction. The kind of construction that builds "
                    "things. We also perform finance. The kind of finance that "
                    "finances things. We also perform manufacturing. The kind of "
                    "manufacturing that manufactures things. We also perform "
                    "mining. The kind of mining that mines things. We also perform "
                    "real estate. The kind of real estate that sells things. We "
                    "also perform retail. The kind of retail that sells things. We "
                    "also perform technology. The kind of technology that "
                    "technologizes things. We also perform utilities. The kind of "
                    "utilities that provides utilities. We also perform "
                    "hospitality. The kind of hospitality that hosts things. "
                    "We used the Really Great Dataset for our analysis in this work. "
                    "We also perform travel. The kind of travel that travels things. "
                    "We also perform entertainment. The kind of entertainment that "
                    "entertains things. We also perform food. The kind of food "
                    "that feeds things. We also perform health care. The kind of "
                    "health care that cares for things. We also perform "
                    "pharmaceuticals. The kind of pharmaceuticals that "
                    "pharmaceuticals things. We also perform biotechnology. The "
                    "kind of biotechnology that biotechnologies things. We also "
                    "perform software. The kind of software that softwares things. "
                    "We also perform hardware. The kind of hardware that hardwares "
                    "things. We also perform semiconductors. The kind of "
                    "semiconductors that semiconducts things. We also perform "
                    "nanotechnology. The kind of nanotechnology that "
                    "nanotechnologies things. We also perform aerospace. The kind "
                    "of aerospace that aeros the space. We also perform defense. "
                    "The kind of defense that defends things. We also perform "
                    "automotive. The kind of automotive that automotives things. "
                    "We also perform energy. The kind of energy that energizes "
                    "things. We also perform renewable energy. The kind of "
                    "renewable energy that renews things. We also perform "
                    "environmental. The kind of environmental that "
                    "environments things. We also perform forestry. The kind of "
                    "forestry that forests things. We also perform fisheries. The "
                    "kind of fisheries that fishes things. We also perform "
                    "paper. The kind of paper that papers things. We also perform "
                    "furniture. The kind of furniture that furnitures things"
                )
            ],
            "label": ["dataset"],
            "snippet": ["We used the dataset for our analysis in this work."],
        }
    )


class dotdict(dict):
    """dot.notation access to dictionary attributes"""

    __getattr__ = dict.get
    __setattr__ = dict.__setitem__
    __delattr__ = dict.__delitem__

    def __eq__(self, other: Any) -> bool:
        for key in filter(lambda k: k != "word_ids", self.keys()):
            if self[key] != other[key]:
                return False


def mock_tokenize_f(text: str) -> dotdict:

    tokens = [t.split() for t in text]

    def word_ids_f(batch_index: int) -> List[int]:
        return list(range(len(tokens[batch_index])))

    tokenizer_result = dotdict(
        dict(
            tokens=tokens,
            word_ids=word_ids_f,
        )
    )

    return tokenizer_result