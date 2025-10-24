from kaldi_active_grammar import KaldiRule, Compiler

compiler = Compiler(model_dir = "vosk-model-cn-kaldi-multicn-0.15")

rule = KaldiRule(
    name="medical_terms",
    rule="(结节 [weight=10.0] | 肺癌 [weight=5.0] | 甲状腺 [weight=3.0])"
)

compiler.compile_grammar(rules=[rule], output_dir="./grammar")
