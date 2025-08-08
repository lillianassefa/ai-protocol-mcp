# Fix for NEX-123: Adjusted login button CSS

def apply_mobile_styles(button_element):
    if screen_width < 480:
        button_element.style.marginLeft = 'auto'
        button_element.style.marginRight = 'auto'
    else:
        button_element.style.marginLeft = '10px'
        button_element.style.marginRight = '10px'

# ... other styles  

