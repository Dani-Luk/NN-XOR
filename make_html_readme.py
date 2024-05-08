"""
# This script is used to convert the README.md file FROM CURRENT FOLDER to a .html file using markdown.
"""
import markdown

with open("README.md", 'r',  encoding='utf-8') as file:
    readme_text = file.read()

html = markdown.markdown(readme_text)
html = f"""
    <html>
        <head>
        <style>
            body {{
                background-color: #f1f1f1;
                //color: #333333;
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Noto Sans', Helvetica, Arial, sans-serif, 'Apple Color Emoji', 'Segoe UI Emoji';
                font-size: 16px;
            }}
            hr {{
                margin-top: -10px;
            }}
            h1 {{
                text-align: center;
                }}
            h2 {{
                padding-bottom: -10px;
                }}
            h3 {{
                margin-left: 20px;
                }}
            h4 {{
                margin-top: -15px;
                margin-left: 20px;                
                margin-bottom: -10px;
                }}
            h5 {{
                font-weight: normal;
                margin-left: 20px;
                margin-top: 0px;
                }}
            hr {{
                border: none;
                height: 1px;
                background: #c3c3c3;
                }}          
            li {{
                margin-top: 5px;
                }}  
            p {{
                margin-left: 20px;
                margin-top: -5px;
                }}
        </style>
    </head>            
<body>
{html}
</body>
</html>
"""

with open("README.html", 'w',  encoding='utf-8') as file:
    file.write(html)    

print("README.html file created successfully.")

import os
from PySide6.QtGui import QIcon, QImage
from PySide6.QtWidgets import QApplication, QStyle


def save_icon_as_ico(icon_size=(16, 16), output_file='arrow_right_16.ico', qStyleIcon = QStyle.SP_ArrowRight):
    path = os.path.abspath(os.path.join(os.path.dirname(__file__), "img_md", output_file))

    # Create a QIcon with the standard arrow right icon
    icon = gApp.style().standardIcon(qStyleIcon)

    # Obtain the standard pixmap for the icon (scaled to desired size)
    pixmap = icon.pixmap(*icon_size)

    # Ensure the pixmap is in RGBA format for .ico compatibility
    pixmap = pixmap.toImage().convertToFormat(QImage.Format_RGBA8888)

    # Save the pixmap as a .ico file
    pixmap.save(path, 'ICO')

    print(f'Icon saved as {output_file}')

# Call the function to save the icon
gApp:QApplication = QApplication.instance()
if gApp is None:
    # if it does not exist then a QApplication is created
    gApp = QApplication()

# save_icon_as_ico()
# save_icon_as_ico(output_file='refresh_16.ico', qStyleIcon= QStyle.SP_BrowserReload)
