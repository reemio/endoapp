# Endoapp3 Project Rules

## UI Requirements

### Icons Usage
- Use `left.png` and `right.png` for navigation between report images (frameless, transparent background)
- Use `record.png` and `stop_record.png` for toggling video recording (single button that changes state)
- Use `camera.png` for image capture functionality
- Use `tick.png` and `delete.png` to replace current tick and X indicators for selection/rejection
- All icons should be displayed without frames or borders
- Icons should appear in their original colors without backgrounds
- Use transparent hover effects instead of solid backgrounds
- Make icons slightly larger (28-30px) for better visibility

### Right Panel
- Keep video feed height less than 65% of panel height
- Remove black bars on video display
- Ensure thumbnails are appropriately sized (not too small)
- Eliminate wasted space in the layout
- Remove double frames on captured media
- Use green/red tick/cross indicators for selected thumbnails (no boxes)
- Add visual indication for captures (flash/icon)
- Make scrollbar automatically follow new captures

### Tab Design
- Remove dark accent on tab bar
- Keep tab design clean and minimal

### Left Panel
- Remove frames around section titles
- No auto-counter for Findings section
- Implement auto-counter for Recommendations and Conclusions sections
- Fix 'ErrorGenID' issue for patient ID
- Remove 'years' text from Age field
- Format Doctor/Designation in ALL CAPS
- Reduce font size for 'Patient Information'/'Report Details' section titles

### Main Window
- Position menu bar lower in the interface
- Add Minimize option to File menu

## System Performance

### Camera System
- Fast initialization is critical - camera should be available instantly
- Skip lengthy resolution testing to ensure immediate startup
- Use reliable VGA (640x480) resolution by default
- Camera stream must start in under 1 second
- UI should be responsive during camera initialization

## Code Standards

### Resource Management
- Always implement proper cleanup methods for QWidgets
- Ensure proper resource deallocation for QPixmap objects
- Release timers and other resources during widget destruction
- Call parent cleanup methods from child widgets

### Documentation
- Document all public methods and classes
- Include parameter descriptions in docstrings
- Document cleanup methods thoroughly

### Testing
- Test resource cleanup during application shutdown
- Verify no memory leaks in UI components
- Test capture and display functionality thoroughly

## Development Workflow
- Document all UI changes in commit messages
- Reference UI rules when implementing new features
- Prioritize fixing UI issues identified in user feedback
