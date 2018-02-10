# javascript.py
#
# Copyright © 2018 Eddy Castillo
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

BODY_JS = '''
document.body.style.backgroundColor = '{bg}';
document.body.style.color = '{fg}';
document.body.style.margin = '60px';
'''

WRAPPER_JS = '''
var wrapper = document.getElementById('SenecaInnerWrapper');

wrapper.style.backgroundColor = '{bg}';
wrapper.style.color = '{fg}';
wrapper.style.margin = '0px {mg}px 0px {mg}px';
wrapper.style.fontFamily = '{fs0}';
wrapper.style.fontWeight = '{fs1}';
wrapper.style.fontStyle = '{fs2}';
wrapper.style.fontStretch = '{fs3}';
wrapper.style.fontSize = '{fs4}px';
wrapper.style.lineHeight = '{lh}';
'''

COL_JS_INNER = '''
function resizeColumn() {
    console.log('resizeColumn was called');
    if (window.innerWidth < 800) {
        console.log('View width less than 800');
        document.body.style.columnWidth = window.innerWidth + 'px';
        document.body.style.height = (window.innerHeight - 120) + 'px';
        console.log('Column width is ' + window.innerWidth + 'px');
    }
    else {
        console.log('View width equal or more than 800');
        document.body.style.columnWidth = Math.floor(window.innerWidth / 2) + 'px';
        document.body.style.height = (window.innerHeight - 120) + 'px';
        document.body.style.columnCount = '2';
        console.log('Column width is ' + Math.floor(window.innerWidth / 2) + 'px');
    }
}
resizeColumn();
window.addEventListener('resize', resizeColumn);
'''

COL_JS = '''
if (!document.getElementById('columnJS')) {{
    var child_script = document.createElement('script');
    child_script.type = 'text/javascript';
    child_script.id = 'columnJS'
    child_script.innerHTML = `{0}`;
    document.body.appendChild(child_script);
}}
document.body.style.overflow = 'hidden';
document.body.style.margin = '60px 0px 60px 0px';
document.body.style.columnGap = '0px';
'''.format(COL_JS_INNER)

COL_JS_REMOVE = '''
if (document.getElementById('columnJS')) {
    document.body.style.columnWidth = 'auto';
    document.body.style.height = 'auto';
    document.body.style.columnCount = 'auto';
    document.body.style.overflow = 'auto';
    document.body.style.margin = 'auto';
    document.body.style.columnGap = 'auto';
    document.body.removeChild(document.getElementById('columnJS'));
}
'''
