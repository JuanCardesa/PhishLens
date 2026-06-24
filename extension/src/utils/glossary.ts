import type { SignalCategoryId } from "./signal-categories";

// Plain-language explanations shown as tooltips next to technical terms in the
// popup and options UI, so non-technical users can hover/focus for context
// without the underlying signal names being hidden or renamed.
export const SIGNAL_GLOSSARY: Partial<Record<SignalCategoryId, string>> = {
  "threat-intel": "Threat intelligence: checks this address against lists of sites already reported as phishing.",
  tls: "TLS: checks whether the site's security certificate (the padlock icon) is valid and not expired.",
  ml: "ML (machine learning): a model trained on real phishing and legitimate URLs adjusts the score based on patterns it learned.",
  "domain-age": "Domain age: how long ago this website's address was first registered. Phishing sites are often very new.",
};

export const CAPABILITY_GLOSSARY: Record<string, string> = {
  "Threat intel": SIGNAL_GLOSSARY["threat-intel"]!,
  TLS: SIGNAL_GLOSSARY.tls!,
  ML: SIGNAL_GLOSSARY.ml!,
  "Domain age": SIGNAL_GLOSSARY["domain-age"]!,
};
