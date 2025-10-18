import curses
import os
import sys
import time
import re

def main(stdscr, initial_page=None):
    curses.curs_set(0)
    stdscr.clear()
    
    h, w = stdscr.getmaxyx()

    # Get the directory where the script is located
    script_dir = os.path.dirname(os.path.abspath(__file__))

    # Read commands from file
    try:
        cmds_path = os.path.join(script_dir, 'cmds.txt')
        with open(cmds_path, 'r', encoding='utf-8') as f:
            raw_lines = [line.rstrip() for line in f]
    except FileNotFoundError:
        raw_lines = ["Error: cmds.txt not found"]
    except Exception as e:
        raw_lines = [f"Error reading file: {str(e)}"]
    
    if not raw_lines:
        raw_lines = ["No page in file"]
    
    # Parse lines into display items
    # (type, display_text, file_name, is_selectable, category)
    all_items = []
    current_category = None
    
    for line in raw_lines:
        if not line.strip():
            continue
        elif line.startswith("### "):
            # Category header - not selectable, adds space before
            text = line[4:]
            current_category = text
            all_items.append(("category", text, None, False, None))
        elif line.startswith("## "):
            # Button with space after
            text = line[3:]
            # Check for filename in parentheses
            match = re.match(r'^(.+?)\s*\((.+?)\)\s*$', text)
            if match:
                display_text = match.group(1).strip()
                file_name = match.group(2).strip()
            else:
                display_text = text
                file_name = text.replace(' ', '_').lower()
            all_items.append(("button_spaced", display_text, file_name, True, current_category))
        else:
            # Regular button
            # Check for filename in parentheses
            match = re.match(r'^(.+?)\s*\((.+?)\)\s*$', line)
            if match:
                display_text = match.group(1).strip()
                file_name = match.group(2).strip()
            else:
                display_text = line
                file_name = line.replace(' ', '_').lower()
            all_items.append(("button", display_text, file_name, True, current_category))
    
    if not all_items:
        all_items = [("button", "No page in file", None, False, None)]
    
    # Search state
    search_mode = False
    search_active = False
    search_query = ""
    display_items = all_items.copy()
    
    # Find first selectable item
    selected_idx = 0
    for i, item in enumerate(display_items):
        if item[3]:  # is_selectable
            selected_idx = i
            break
    
    scroll_offset = 0
    about_text = []
    about_scroll = 0
    focus = "pages"  # "pages" or "about"

    # Handle initial page selection if provided
    if initial_page:
        # Normalize the search query (join args and convert to lowercase)
        initial_page_lower = initial_page.lower()
        
        # Try to find matching page
        for i, item in enumerate(all_items):
            if item[3]:  # is_selectable
                # Check both display text and filename
                if (initial_page_lower in item[1].lower() or 
                    (item[2] and initial_page_lower in item[2].lower())):
                    selected_idx = i
                    # Auto-open the page
                    file_path = os.path.join(script_dir, 'guides', item[2])
                    if not file_path.endswith('.txt'):
                        file_path += '.txt'
                    try:
                        with open(file_path, 'r', encoding='utf-8') as f:
                            about_text = f.read().splitlines()
                        about_scroll = 0
                    except FileNotFoundError:
                        about_text = [f"No information found for {item[1]}", "", f"Expected file: {file_path}"]
                        about_scroll = 0
                    except Exception as e:
                        about_text = [f"Error loading file: {str(e)}"]
                        about_scroll = 0
                    break

    def filter_items_by_search(query):
        """Filter items by search query and group by category."""
        if not query:
            return all_items.copy()
        
        query_lower = query.lower()
        
        # Find all matching items
        matching_items = [item for item in all_items 
                         if item[3] and query_lower in item[1].lower()]  # Only search selectable items
        
        if not matching_items:
            return [("button", "No results found", None, False, None)]
        
        # Group by category
        categories = {}
        for item in matching_items:
            cat = item[4] if item[4] else "Uncategorized"
            if cat not in categories:
                categories[cat] = []
            categories[cat].append(item)
        
        # Build display list with categories
        result = []
        for i, (cat_name, items) in enumerate(categories.items()):
            # Add blank space before category (except first)
            if i > 0:
                result.append(("spacer", "", None, False, None))
            # Add category header
            result.append(("category", cat_name, None, False, None))
            # Add items in this category (without spacing)
            for item in items:
                item_type, display_text, file_name, is_selectable, _ = item
                result.append(("button", display_text, file_name, is_selectable, cat_name))
        
        return result

    while True:
        stdscr.clear()
        h, w = stdscr.getmaxyx()
        
        if h < 10 or w < 50:
            stdscr.addstr(0, 0, "Terminal too small (min 50x10)")
            stdscr.refresh()
            key = stdscr.getch()
            if key in [10, 13, ord('q'), ord('Q')]:
                break
            continue
        
        try:
            stdscr.box()

            title = "Help Guide"
            title_x = max(1, w//2 - len(title)//2)
            if title_x + len(title) < w - 1 and h > 1:
                stdscr.addstr(1, title_x, title)

            button_label = "[Quit (Press Q)]"
            button_x = w - len(button_label) - 2
            if button_x > 0 and h > 1:
                stdscr.addstr(1, button_x, button_label, curses.A_REVERSE)

            cmd_box_height = h - 4
            cmd_box_width = min(40, w - 4)
            cmd_box_start_y = 3
            cmd_box_start_x = 2

            about_box_width = w - cmd_box_width - 6
            about_box_height = cmd_box_height
            about_box_start_y = 3
            about_box_start_x = cmd_box_start_x + cmd_box_width + 2

            # Draw commands box
            if cmd_box_height >= 3 and cmd_box_width >= 10:
                for y in range(cmd_box_height):
                    box_y = cmd_box_start_y + y
                    if box_y >= h - 1:
                        break
                    for x in range(cmd_box_width):
                        box_x = cmd_box_start_x + x
                        if box_x >= w - 1:
                            break
                        try:
                            if y == 0 or y == cmd_box_height - 1:
                                if x == 0:
                                    stdscr.addch(box_y, box_x, curses.ACS_ULCORNER if y == 0 else curses.ACS_LLCORNER)
                                elif x == cmd_box_width - 1:
                                    stdscr.addch(box_y, box_x, curses.ACS_URCORNER if y == 0 else curses.ACS_LRCORNER)
                                else:
                                    stdscr.addch(box_y, box_x, curses.ACS_HLINE)
                            elif x == 0 or x == cmd_box_width - 1:
                                stdscr.addch(box_y, box_x, curses.ACS_VLINE)
                        except curses.error:
                            pass
                
                # Draw title with search indicator
                if search_mode:
                    txt = f"Search: {search_query}_"
                elif search_active:
                    txt = f"Filtered: {search_query}"
                else:
                    txt = "Pages" if focus != "pages" else "Pages (active)"
                txt_x = cmd_box_start_x + ((cmd_box_width // 2) - (len(txt) // 2))
                if txt_x >= 0 and txt_x + len(txt) < w and cmd_box_start_y < h:
                    try:
                        attr = curses.A_BOLD if focus == "pages" or search_mode or search_active else curses.A_NORMAL
                        stdscr.addstr(cmd_box_start_y, txt_x, txt[:cmd_box_width-2], attr)
                    except curses.error:
                        pass

            # Draw about box
            if about_box_width > 10 and about_box_start_x + about_box_width < w:
                for y in range(about_box_height):
                    box_y = about_box_start_y + y
                    if box_y >= h - 1:
                        break
                    for x in range(about_box_width):
                        box_x = about_box_start_x + x
                        if box_x >= w - 1:
                            break
                        try:
                            if y == 0 or y == about_box_height - 1:
                                if x == 0:
                                    stdscr.addch(box_y, box_x, curses.ACS_ULCORNER if y == 0 else curses.ACS_LLCORNER)
                                elif x == about_box_width - 1:
                                    stdscr.addch(box_y, box_x, curses.ACS_URCORNER if y == 0 else curses.ACS_LRCORNER)
                                else:
                                    stdscr.addch(box_y, box_x, curses.ACS_HLINE)
                            elif x == 0 or x == about_box_width - 1:
                                stdscr.addch(box_y, box_x, curses.ACS_VLINE)
                        except curses.error:
                            pass
                
                about_title = "About" if focus != "about" else "About (active)"
                about_title_x = about_box_start_x + ((about_box_width // 2) - (len(about_title) // 2))
                if about_title_x >= 0 and about_title_x + len(about_title) < w and about_box_start_y < h:
                    try:
                        attr = curses.A_BOLD if focus == "about" else curses.A_NORMAL
                        stdscr.addstr(about_box_start_y, about_title_x, about_title, attr)
                    except curses.error:
                        pass

            # Calculate display rows with proper spacing
            visible_rows = max(1, cmd_box_height - 2)
            
            # Build list of display rows considering spacing
            # In search mode, we don't add spacing for button_spaced
            display_rows = []  # (item_idx, skip_display)
            for i, item in enumerate(display_items):
                item_type = item[0]
                # Spacer items are just for spacing, don't display them
                skip_display = (item_type == "spacer")
                display_rows.append((i, skip_display))
            
            # Find which display row corresponds to selected_idx
            selected_display_row = 0
            for dr_idx, (item_idx, _) in enumerate(display_rows):
                if item_idx == selected_idx:
                    selected_display_row = dr_idx
                    break
            
            # Calculate actual row position accounting for spacing
            actual_row_positions = []
            current_row = 0
            for item_idx, skip_display in display_rows:
                if skip_display:
                    # Spacer takes up a row but doesn't display
                    current_row += 1
                    actual_row_positions.append(current_row)
                else:
                    actual_row_positions.append(current_row)
                    current_row += 1
                    # Add space after button_spaced items ONLY when not in search mode
                    if not search_active and display_items[item_idx][0] == "button_spaced":
                        current_row += 1
            
            selected_actual_row = actual_row_positions[selected_display_row] if selected_display_row < len(actual_row_positions) else 0
            
            # Adjust scroll_offset to keep selected item visible
            if selected_actual_row < scroll_offset:
                scroll_offset = selected_actual_row
            elif selected_actual_row >= scroll_offset + visible_rows:
                scroll_offset = selected_actual_row - visible_rows + 1
            
            # Ensure scroll_offset doesn't go negative
            scroll_offset = max(0, scroll_offset)
            
            # Display commands/categories/items
            display_row = 0
            actual_row = 0
            
            for item_idx, skip_display in display_rows:
                # Skip spacer items (they just create blank lines)
                if skip_display:
                    actual_row += 1
                    if actual_row > scroll_offset:
                        display_row += 1
                    continue
                
                # Check if this row should be displayed
                if actual_row < scroll_offset:
                    actual_row += 1
                    # Add space after button_spaced items ONLY when not in search mode
                    if not search_active and display_items[item_idx][0] == "button_spaced":
                        actual_row += 1
                    continue
                
                if display_row >= visible_rows:
                    break
                
                item_type, display_text, file_name, is_selectable, category = display_items[item_idx]
                
                max_text_width = cmd_box_width - 4
                truncated_text = display_text
                if len(display_text) > max_text_width:
                    truncated_text = display_text[:max_text_width - 3] + "..."
                
                y_pos = cmd_box_start_y + 1 + display_row
                x_pos = cmd_box_start_x + 2
                
                if y_pos >= h - 1 or x_pos + len(truncated_text) >= w - 1:
                    break
                
                try:
                    if item_type == "category":
                        # Display as bold/underlined category header
                        stdscr.addstr(y_pos, x_pos, truncated_text, curses.A_BOLD | curses.A_UNDERLINE)
                    elif item_idx == selected_idx and focus == "pages" and not search_mode:
                        # Selected button
                        stdscr.addstr(y_pos, x_pos, truncated_text, curses.A_REVERSE)
                    else:
                        # Regular button
                        stdscr.addstr(y_pos, x_pos, truncated_text)
                except curses.error:
                    pass
                
                display_row += 1
                actual_row += 1
                
                # Add space after button_spaced items ONLY when not in search mode
                if not search_active and item_type == "button_spaced":
                    display_row += 1
                    actual_row += 1

            # Display about text with proper scrolling
            if about_box_width > 10 and about_box_start_x + about_box_width < w:
                visible_about_rows = max(1, about_box_height - 2)
                
                # Ensure about_scroll is within bounds
                max_about_scroll = max(0, len(about_text) - visible_about_rows)
                about_scroll = max(0, min(about_scroll, max_about_scroll))
                
                for i in range(visible_about_rows):
                    line_idx = about_scroll + i
                    if line_idx >= len(about_text):
                        break
                    
                    line = about_text[line_idx]
                    max_about_width = about_box_width - 4
                    if len(line) > max_about_width:
                        line = line[:max_about_width]
                    
                    y_pos = about_box_start_y + 1 + i
                    x_pos = about_box_start_x + 2
                    
                    if y_pos >= h - 1 or x_pos + len(line) >= w - 1:
                        continue
                    
                    try:
                        stdscr.addstr(y_pos, x_pos, line)
                    except curses.error:
                        pass

        except curses.error:
            pass

        try:
            stdscr.refresh()
        except curses.error:
            pass

        key = stdscr.getch()
        
        # Handle search mode input
        if search_mode:
            if key == 27:  # ESC - exit search but keep filter active
                search_mode = False
                search_active = True if search_query else False
            elif key in [curses.KEY_BACKSPACE, 127, 8]:  # Backspace
                if search_query:
                    search_query = search_query[:-1]
                    # Filter items
                    if search_query:
                        display_items = filter_items_by_search(search_query)
                        search_active = True
                    else:
                        display_items = all_items.copy()
                        search_active = False
                    # Reset selection
                    selected_idx = 0
                    for i, item in enumerate(display_items):
                        if item[3]:
                            selected_idx = i
                            break
                    scroll_offset = 0
            elif key in [10, 13]:  # Enter - exit search and select
                search_mode = False
                search_active = True if search_query else False
                if display_items and selected_idx < len(display_items):
                    item_type, display_text, file_name, is_selectable, category = display_items[selected_idx]
                    if is_selectable and file_name:
                        file_path = os.path.join(script_dir, 'guides', file_name)
                        if not file_path.endswith('.txt'):
                            file_path += '.txt'
                        try:
                            with open(file_path, 'r', encoding='utf-8') as f:
                                about_text = f.read().splitlines()
                            about_scroll = 0
                        except FileNotFoundError:
                            about_text = [f"No information found for {display_text}", "", f"Expected file: {file_path}"]
                            about_scroll = 0
                        except Exception as e:
                            about_text = [f"Error loading file: {str(e)}"]
                            about_scroll = 0
            elif 32 <= key <= 126:  # Printable characters
                search_query += chr(key)
                # Filter items
                display_items = filter_items_by_search(search_query)
                search_active = True
                # Reset selection
                selected_idx = 0
                for i, item in enumerate(display_items):
                    if item[3]:
                        selected_idx = i
                        break
                scroll_offset = 0
        else:
            # Normal mode input
            if key in [10, 13]:  # Enter
                if focus == "pages" and selected_idx < len(display_items):
                    item_type, display_text, file_name, is_selectable, category = display_items[selected_idx]
                    if is_selectable and file_name:
                        file_path = os.path.join(script_dir, 'guides', file_name)
                        if not file_path.endswith('.txt'):
                            file_path += '.txt'
                        try:
                            with open(file_path, 'r', encoding='utf-8') as f:
                                about_text = f.read().splitlines()
                            about_scroll = 0
                        except FileNotFoundError:
                            about_text = [f"No information found for {display_text}", "", f"Expected file: {file_path}"]
                            about_scroll = 0
                        except Exception as e:
                            about_text = [f"Error loading file: {str(e)}"]
                            about_scroll = 0
            elif key == curses.KEY_UP:
                if focus == "pages":
                    # Find previous selectable item
                    new_idx = selected_idx - 1
                    while new_idx >= 0 and not display_items[new_idx][3]:
                        new_idx -= 1
                    if new_idx >= 0:
                        selected_idx = new_idx
                elif focus == "about":
                    if about_scroll > 0:
                        about_scroll -= 1
            elif key == curses.KEY_DOWN:
                if focus == "pages":
                    # Find next selectable item
                    new_idx = selected_idx + 1
                    while new_idx < len(display_items) and not display_items[new_idx][3]:
                        new_idx += 1
                    if new_idx < len(display_items):
                        selected_idx = new_idx
                elif focus == "about":
                    max_about_scroll = max(0, len(about_text) - (about_box_height - 2))
                    if about_scroll < max_about_scroll:
                        about_scroll += 1
            elif key == curses.KEY_PPAGE:  # Page Up
                if focus == "about":
                    about_scroll = max(0, about_scroll - (about_box_height - 2))
            elif key == curses.KEY_NPAGE:  # Page Down
                if focus == "about":
                    max_about_scroll = max(0, len(about_text) - (about_box_height - 2))
                    about_scroll = min(max_about_scroll, about_scroll + (about_box_height - 2))
            elif key == curses.KEY_LEFT:
                focus = "pages"
            elif key == curses.KEY_RIGHT:
                focus = "about"
            elif key in [ord('/'), ord('f'), ord('F')]:  # Start search
                search_mode = True
                search_query = ""
                focus = "pages"
            elif key == ord('c') or key == ord('C'):  # Clear search filter
                if search_active:
                    search_active = False
                    search_query = ""
                    display_items = all_items.copy()
                    selected_idx = 0
                    for i, item in enumerate(display_items):
                        if item[3]:
                            selected_idx = i
                            break
                    scroll_offset = 0
            elif key == ord('q') or key == ord('Q'):
                break

if __name__ == "__main__":
    time.sleep(0.1)
    
    # Get command-line argument for initial page
    initial_page = None
    if len(sys.argv) > 1:
        # Join all arguments after the script name (for multi-word page names)
        initial_page = ' '.join(sys.argv[1:])
    
    curses.wrapper(lambda stdscr: main(stdscr, initial_page))
