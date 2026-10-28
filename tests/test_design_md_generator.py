from core.design_tokens import DesignTokens, ColorTokens, TypeToken, ComponentToken
from core.design_md_generator import generate_design_md, _has_font

def test_font_regex():
    assert _has_font(['Inter-Regular'], ['Inter']) is True
    assert _has_font(['Interesting-Sans'], ['Inter']) is False
    assert _has_font(['Caveat'], ['Caveat']) is True
    assert _has_font(['NotACaveatHere'], ['Caveat']) is False
    assert _has_font(['Playfair Display'], ['Playfair']) is True
    print("test_font_regex passed")

def test_empty_tokens():
    empty_tokens = DesignTokens()
    md_empty = generate_design_md(empty_tokens, 'Empty Design')
    assert '<design-context>' in md_empty
    assert '</design-context>' in md_empty
    assert 'name: "empty-design-design-analysis"' in md_empty
    assert '# NOTE: no component classes were detected in the source.' in md_empty
    assert 'base: 4px' in md_empty
    assert 'Brand Gradient' not in md_empty
    assert '### Semantic' not in md_empty
    assert 'violet' not in md_empty
    assert 'cyan' not in md_empty
    assert 'gradient-develop' not in md_empty
    assert '#7928ca' not in md_empty
    assert '#ff0080' not in md_empty
    assert '#f9cb28' not in md_empty
    print("test_empty_tokens passed")

def test_populated_tokens():
    tokens = DesignTokens(
        theme='light',
        fonts=['Inter', 'Caveat'],
        display_font='Caveat',
        body_font='Inter',
        mono_font='Fira Code',
        colors=ColorTokens(
            canvas='#fefefe',
            surface='#f5f5f5',
            surface_2='#eeeeee',
            ink='#111111',
            body='#444444',
            muted='#888888',
            border='#cccccc',
            border_strong='#999999',
            primary_accent='#3b82f6',
            on_primary='#ffffff',
            link='#2563eb',
            link_deep='#1d4ed8',
            link_soft='#dbeafe',
            semantic={'success': '#10b981', 'error': '#ef4444'},
            gradients=[('#3b82f6', '#8b5cf6')],
        ),
        typography={
            'display-xl': TypeToken(font_family='Caveat', font_size='48px', font_weight='700', line_height='52px', letter_spacing='-1px'),
            'body-md': TypeToken(font_family='Inter', font_size='16px', font_weight='400', line_height='24px', letter_spacing='0px'),
            'empty-bucket': TypeToken(font_family='', font_size='', font_weight='', line_height=''),
        },
        spacing=[4, 8, 16, 24, 192],
        radii=['4px', '8px', '16px', 'full'],
        components=[
            ComponentToken(name='card-polaroid', kind='scrapbook', selector='.card-polaroid', properties={'background': '#fff', 'padding': '16px', 'border-radius': '8px'}),
        ]
    )

    md = generate_design_md(tokens, 'Polaroid Studio')
    assert 'Creative Scrapbook & Visual Narrative' in md
    assert 'canvas: "#fefefe"' in md
    assert 'success: "#10b981"' in md
    assert 'error: "#ef4444"' in md
    assert 'warning:' not in md  # warning wasn't provided, so omitted!
    assert 'info:' not in md     # info wasn't provided, so omitted!
    assert 'gradient-1-start: "#3b82f6"' in md
    assert 'gradient-1-end: "#8b5cf6"' in md
    assert '### Brand Gradient' in md
    assert '### Semantic' in md
    assert 'empty-bucket' not in md  # empty bucket skipped!
    assert 'full: 9999px' in md
    assert '# NOTE: 9999px is a universal CSS idiom for fully-rounded' in md
    assert 'section: 192px' in md
    assert 'card-polaroid:' in md
    assert '# kind: scrapbook' in md
    assert 'Scrapbook Components' in md
    print("test_populated_tokens passed")

if __name__ == "__main__":
    test_font_regex()
    test_empty_tokens()
    test_populated_tokens()
    print("ALL TESTS PASSED SUCCESSFULLY!")
