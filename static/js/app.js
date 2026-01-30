// Main application logic - Fixes nodes crossing & collision issues
document.addEventListener('DOMContentLoaded', function () {
    const form = document.getElementById('sankeyForm');
    const submitBtn = document.getElementById('submitBtn');
    const errorMessage = document.getElementById('errorMessage');
    const resultContainer = document.getElementById('resultContainer');
    const resultTitle = document.getElementById('resultTitle');
    const sankeyDiagram = document.getElementById('sankeyDiagram');
    const sankeyRawText = document.getElementById('sankeyRawText');
    const sankeyRawTextContainer = document.getElementById('sankeyRawTextContainer');
    const downloadBtn = document.getElementById('downloadBtn');
    const submitAllBtn = document.getElementById('submitAllBtn');

    // --- Helpers ---
    const formatActualP = (p) => {
        if (!p) return '';
        if (p.includes('-Q')) {
            const [y, q] = p.split('-Q');
            return `Quý ${q} ${y}`;
        }
        if (/^\d{4}$/.test(p)) return `Cả Năm ${p}`;
        return p;
    };

    const addRotateButton = () => {
        if (window.innerWidth < 768) {
            const buttonGroup = resultContainer.querySelector('.button-group');
            if (buttonGroup && !buttonGroup.querySelector('.btn-rotate')) {
                const rotateBtn = document.createElement('button');
                rotateBtn.className = 'btn-rotate';
                rotateBtn.innerHTML = `
                    <svg width="16" height="16" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"></path>
                    </svg>
                    Xoay Biểu Đồ
                `;
                rotateBtn.addEventListener('click', () => {
                    sankeyDiagram.classList.toggle('rotated');
                    rotateBtn.classList.toggle('active');
                });
                buttonGroup.insertBefore(rotateBtn, buttonGroup.firstChild);
            }
        }
    };

    // --- Sankey Settings State ---
    const sankeySettings = {
        diagramWidth: window.innerWidth < 768 ? Math.max(800, window.innerWidth - 40) : 1100,
        diagramHeight: window.innerWidth < 768 ? 500 : 600,
        // Match SankeyMATIC-style semantics:
        // - nodeHeightFactor: 0..1 (SankeyMATIC default = 0.5)
        // - nodeSpacing: 0..100 meaning "spacing factor %" (SankeyMATIC default = 85)
        nodeHeightFactor: 0.5,
        nodeSpacing: 85,
        nodeWidth: 9,
        nodeOpacity: 1.0,
        nodeBorder: 0,
        // Layout Options
        leftJustifyOrigins: false,
        rightJustifyEndpoints: true,
        // SankeyMATIC defaults:
        flowOpacity: 0.45,
        flowCurvature: 0.5,
        layoutIterations: 25,
        palette: ["#3b82f6", "#10b981", "#f59e0b", "#8b5cf6", "#ef4444", "#06b6d4", "#ec4899", "#84cc16", "#f43f5e", "#94a3b8"]
    };

    // --- Custom Dropdown Manager ---
    function initCustomDropdown(selectorId, triggerId, listId, displayId, inputId, onSelect = null) {
        const selector = document.getElementById(selectorId);
        const trigger = document.getElementById(triggerId);
        const list = document.getElementById(listId);
        const display = document.getElementById(displayId);
        const input = document.getElementById(inputId);

        if (!selector || !list || !trigger) return;

        // Toggle visibility
        trigger.addEventListener('click', (e) => {
            e.stopPropagation();
            // Close all other open dropdowns first
            document.querySelectorAll('.custom-dropdown').forEach(d => {
                if (d !== selector) d.classList.remove('active');
            });
            selector.classList.toggle('active');
        });

        // Toggle logic for items already in HTML
        const items = list.querySelectorAll('.dropdown-item');
        items.forEach(item => {
            item.addEventListener('click', () => {
                const val = item.dataset.value;
                input.value = val;
                display.textContent = item.textContent;

                list.querySelectorAll('.dropdown-item').forEach(el => el.classList.remove('selected'));
                item.classList.add('selected');

                selector.classList.remove('active');
                if (onSelect) onSelect(val);
                if (lastSankeyText) renderSankeyDiagram(lastSankeyText, lastFormData);
            });
        });

        // Close on click outside
        document.addEventListener('click', (e) => {
            if (!selector.contains(e.target)) {
                selector.classList.remove('active');
            }
        });

        return {
            addItem: (text, value, isSelected = false) => {
                const item = document.createElement('div');
                item.className = 'dropdown-item';
                if (isSelected) {
                    item.classList.add('selected');
                    input.value = value;
                    display.textContent = text;
                }
                item.textContent = text;
                item.dataset.value = value;

                item.addEventListener('click', () => {
                    input.value = value;
                    display.textContent = text;
                    list.querySelectorAll('.dropdown-item').forEach(el => el.classList.remove('selected'));
                    item.classList.add('selected');
                    selector.classList.remove('active');
                    if (onSelect) onSelect(value);
                    if (lastSankeyText) renderSankeyDiagram(lastSankeyText, lastFormData);
                });

                list.appendChild(item);
            },
            clearItems: () => {
                list.innerHTML = '';
            }
        };
    }

    // Initialize Report Type and Period
    initCustomDropdown('reportTypeSelector', 'reportTypeTrigger', 'reportTypeList', 'reportTypeDisplay', 'reportType');
    initCustomDropdown('periodSelector', 'periodTrigger', 'periodList', 'periodDisplay', 'period');

    // Initialize Year Dropdown with dynamic population
    const yearDropdown = initCustomDropdown('yearSelector', 'yearTrigger', 'yearList', 'yearDisplay', 'year');
    if (yearDropdown) {
        const currentYear = new Date().getFullYear();
        const startYear = 2010;
        const endYear = currentYear;

        yearDropdown.clearItems();
        for (let y = endYear; y >= startYear; y--) {
            yearDropdown.addItem(y.toString(), y.toString(), y === currentYear);
        }
    }

    let lastSankeyText = null;
    let lastFormData = null;

    // --- Settings Listeners ---
    const settingsIds = ['diagramWidth', 'diagramHeight', 'nodeHeightFactor', 'nodeSpacing', 'nodeWidth', 'nodeOpacity', 'nodeBorder'];
    settingsIds.forEach(id => {
        const input = document.getElementById(id);
        const valDisplay = document.getElementById(id + 'Val');

        if (input && valDisplay) {
            input.addEventListener('input', (e) => {
                let val = parseFloat(e.target.value);
                if (id === 'nodeHeightFactor') {
                    sankeySettings[id] = val / 100;
                    valDisplay.textContent = val + '%';
                } else if (id === 'nodeOpacity') {
                    sankeySettings[id] = val / 100;
                    valDisplay.textContent = (val / 100).toFixed(1);
                } else {
                    sankeySettings[id] = val;
                    if (id === 'nodeSpacing') {
                        valDisplay.textContent = val + '%';
                    } else {
                        valDisplay.textContent = (id.includes('Width') || id.includes('Height') || id === 'nodeBorder' ? val + 'px' : val);
                    }
                }

                if (lastSankeyText) renderSankeyDiagram(lastSankeyText, lastFormData);
            });
        }
    });

    // Checkbox Listeners
    ['leftJustifyOrigins', 'rightJustifyEndpoints'].forEach(id => {
        const input = document.getElementById(id);
        if (input) {
            input.addEventListener('change', (e) => {
                sankeySettings[id] = e.target.checked;
                if (lastSankeyText) renderSankeyDiagram(lastSankeyText, lastFormData);
            });
        }
    });

    // Palette Listeners
    for (let i = 1; i <= 10; i++) {
        const input = document.getElementById(`paletteColor${i}`);
        if (input) {
            input.addEventListener('input', (e) => {
                sankeySettings.palette[i - 1] = e.target.value;
                if (lastSankeyText) renderSankeyDiagram(lastSankeyText, lastFormData);
            });
        }
    }

    // --- PNG Export Handler ---
    document.getElementById('downloadPngBtn')?.addEventListener('click', () => {
        const svgElement = document.querySelector('#sankeyDiagram svg');
        if (svgElement) exportSvgToPng(svgElement, lastFormData);
    });

    function exportSvgToPng(svgElement, formData) {
        // Clone the SVG to avoid modifying the visible one during export
        const cloneSvg = svgElement.cloneNode(true);

        const width = parseInt(svgElement.getAttribute('width'));
        const height = parseInt(svgElement.getAttribute('height'));

        // Ensure the clone has explicit dimensions
        cloneSvg.setAttribute('width', width);
        cloneSvg.setAttribute('height', height);

        const svgData = new XMLSerializer().serializeToString(cloneSvg);
        const canvas = document.createElement('canvas');
        const ctx = canvas.getContext('2d');
        const img = new Image();

        canvas.width = width;
        canvas.height = height;

        const svgBlob = new Blob([svgData], { type: 'image/svg+xml;charset=utf-8' });
        const url = URL.createObjectURL(svgBlob);

        img.onload = () => {
            ctx.fillStyle = 'white';
            ctx.fillRect(0, 0, width, height);
            ctx.drawImage(img, 0, 0);
            URL.revokeObjectURL(url);

            const reportCode = formData.report_type || 'all';
            const periodCode = formData.period;
            const pngUrl = canvas.toDataURL('image/png');
            const a = document.createElement('a');
            a.href = pngUrl;
            a.download = `sankey_${formData.symbol}_${reportCode}_${periodCode}_${formData.year}.png`;
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
        };
        img.onerror = () => {
            console.error("Failed to load SVG for export");
            URL.revokeObjectURL(url);
        };
        img.src = url;
    }

    // --- Form Submission ---
    form.addEventListener('submit', async (e) => {
        e.preventDefault();

        const formData = {
            symbol: document.getElementById('symbol').value.trim().toUpperCase(),
            report_type: document.getElementById('reportType').value,
            period: document.getElementById('period').value,
            year: parseInt(document.getElementById('year').value)
        };

        submitBtn.disabled = true;
        submitBtn.textContent = 'Đang xử lý...';
        errorMessage.style.display = 'none';
        resultContainer.style.display = 'none';

        try {
            const response = await fetch('/api/generate-sankey', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(formData)
            });

            const data = await response.json();

            if (!response.ok || !data.success) {
                throw new Error(data.error || 'Có lỗi xảy ra khi tạo biểu đồ');
            }

            // Year Mismatch Warning
            if (data.actual_period && !data.actual_period.includes(formData.year.toString())) {
                errorMessage.innerHTML = `⚠️ Lưu ý: Không tìm thấy dữ liệu cho năm ${formData.year}. Hệ thống đang hiển thị dữ liệu mới nhất có sẵn: <strong>${data.actual_period}</strong>.`;
                errorMessage.style.background = 'rgba(245, 158, 11, 0.1)';
                errorMessage.style.borderColor = '#f59e0b';
                errorMessage.style.color = '#fde68a';
                errorMessage.style.display = 'block';
            } else {
                errorMessage.style.display = 'none';
                // Reset styles if it was a warning before
                errorMessage.style.background = '';
                errorMessage.style.borderColor = '';
                errorMessage.style.color = '';
            }

            const reportNames = { 'balance': 'Bảng Cân Đối Kế Toán', 'income': 'Báo Cáo Kết Quả Kinh Doanh', 'cashflow': 'Báo Cáo Lưu Chuyển Tiền Tệ' };
            const periodNames = { 'Q1': 'Quý I', 'Q2': 'Quý II', 'Q3': 'Quý III', 'Q4': 'Quý IV', 'year': 'Cả Năm' };

            const displayPeriod = data.actual_period ? formatActualP(data.actual_period) : `${periodNames[formData.period]} ${formData.year}`;

            resultTitle.innerHTML = `
                <div class="result-title-main">${reportNames[formData.report_type]}</div>
                <div class="result-title-sub">${formData.symbol} | ${displayPeriod} | Đơn vị: Tỷ VNĐ</div>
            `;

            addRotateButton();

            lastSankeyText = data.data;
            // Update formData with actual period for SVG title
            lastFormData = { ...formData, actual_period_text: displayPeriod };
            sankeyRawText.textContent = data.data;
            sankeyRawTextContainer.style.display = 'block';
            resultContainer.style.display = 'block';

            // Hide initial state message
            const initialState = document.getElementById('initialState');
            if (initialState) initialState.style.display = 'none';

            renderSankeyDiagram(data.data, formData);

        } catch (error) {
            console.error('Error:', error);
            errorMessage.textContent = error.message;
            errorMessage.style.background = 'rgba(239, 68, 68, 0.1)';
            errorMessage.style.borderColor = 'var(--error)';
            errorMessage.style.color = '#fca5a5';
            errorMessage.style.display = 'block';
        } finally {
            submitBtn.disabled = false;
            submitBtn.textContent = 'Tạo Biểu Đồ';
        }
    });

    // --- Submit All Reports ---
    submitAllBtn.addEventListener('click', async () => {
        const formData = {
            symbol: document.getElementById('symbol').value.trim().toUpperCase(),
            period: document.getElementById('period').value,
            year: parseInt(document.getElementById('year').value)
        };

        if (!formData.symbol) {
            alert('Vui lòng nhập mã cổ phiếu');
            return;
        }

        submitAllBtn.disabled = true;
        submitBtn.disabled = true;
        submitAllBtn.textContent = 'Đang xử lý...';
        errorMessage.style.display = 'none';
        resultContainer.style.display = 'none';

        try {
            const response = await fetch('/api/generate-all-reports', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(formData)
            });

            const data = await response.json();

            if (!response.ok || !data.success) {
                throw new Error(data.error || 'Có lỗi xảy ra khi tạo báo cáo');
            }

            // Batch Year Mismatch Warning
            const mismatched = [];
            if (data.actual_periods) {
                for (const [key, ap] of Object.entries(data.actual_periods)) {
                    if (ap && !ap.includes(formData.year.toString())) {
                        mismatched.push(ap);
                    }
                }
            }

            if (mismatched.length > 0) {
                const uniqueActuals = [...new Set(mismatched)].join(', ');
                errorMessage.innerHTML = `⚠️ Lưu ý: Không tìm thấy đầy đủ dữ liệu ${formData.year}. Đang hiển thị dữ liệu mới nhất: <strong>${uniqueActuals}</strong>.`;
                errorMessage.style.background = 'rgba(245, 158, 11, 0.1)';
                errorMessage.style.borderColor = '#f59e0b';
                errorMessage.style.color = '#fde68a';
                errorMessage.style.display = 'block';
            } else {
                errorMessage.style.display = 'none';
                errorMessage.style.background = '';
                errorMessage.style.borderColor = '';
                errorMessage.style.color = '';
            }

            // Prepare UI for multiple charts
            const periodNames = { 'Q1': 'Quý I', 'Q2': 'Quý II', 'Q3': 'Quý III', 'Q4': 'Quý IV', 'year': 'Cả Năm' };

            resultTitle.innerHTML = `
                <div class="result-title-main">Báo Cáo Tài Chính Tổng Hợp</div>
                <div class="result-title-sub">${formData.symbol} | ${periodNames[formData.period]} ${formData.year} | Đơn vị: Tỷ VNĐ</div>
            `;

            addRotateButton();

            sankeyDiagram.innerHTML = '<div class="multi-charts-container"></div>';
            const multiContainer = sankeyDiagram.querySelector('.multi-charts-container');

            const reportNames = {
                'balance': 'Bảng Cân Đối Kế Toán',
                'income': 'Kết Quả Kinh Doanh',
                'cashflow': 'Lưu Chuyển Tiền Tệ'
            };

            // Render each chart
            ['balance', 'income', 'cashflow'].forEach(type => {
                if (data.data[type] && !data.data[type].startsWith('// Error')) {
                    const wrapper = document.createElement('div');
                    wrapper.className = 'chart-wrapper';
                    wrapper.id = `chart-${type}`;

                    const actualP = data.actual_periods?.[type] || '';
                    const isMismatch = actualP && !actualP.includes(formData.year.toString());

                    const titleDiv = document.createElement('div');
                    titleDiv.className = 'chart-title-container';
                    titleDiv.style.display = 'flex';
                    titleDiv.style.justifyContent = 'space-between';
                    titleDiv.style.alignItems = 'center';

                    const tagWrapper = document.createElement('div');
                    tagWrapper.style.display = 'flex';
                    tagWrapper.style.alignItems = 'center';
                    tagWrapper.style.gap = '8px';

                    const tag = document.createElement('span');
                    tag.className = 'chart-type-tag';
                    tag.textContent = reportNames[type];
                    tagWrapper.appendChild(tag);

                    if (isMismatch) {
                        const warnTag = document.createElement('span');
                        warnTag.style.fontSize = '0.75rem';
                        warnTag.style.color = '#f59e0b';
                        warnTag.style.fontWeight = '600';
                        warnTag.textContent = `(Dữ liệu: ${formatActualP(actualP)})`;
                        tagWrapper.appendChild(warnTag);
                    }
                    titleDiv.appendChild(tagWrapper);

                    const dlBtn = document.createElement('button');
                    dlBtn.className = 'btn-download';
                    dlBtn.style.padding = '0.3rem 0.6rem';
                    dlBtn.style.fontSize = '0.75rem';
                    dlBtn.innerHTML = `
                        <svg width="14" height="14" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
                                d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z">
                            </path>
                        </svg>
                        Lưu PNG
                    `;
                    titleDiv.appendChild(dlBtn);

                    wrapper.appendChild(titleDiv);

                    const chartDiv = document.createElement('div');
                    chartDiv.className = 'sankey-item-diagram';
                    chartDiv.style.overflowX = 'auto'; // Support scroll for horizontal ratio
                    wrapper.appendChild(chartDiv);

                    multiContainer.appendChild(wrapper);

                    // We need a specific formData for each render to get the title right in SVG
                    const specificFormData = {
                        ...formData,
                        report_type: type,
                        actual_period_text: isMismatch ? formatActualP(actualP) : `${periodNames[formData.period]} ${formData.year}`
                    };
                    renderSankeyDiagram(data.data[type], specificFormData, chartDiv);

                    // Add click listener for this specific download button
                    dlBtn.addEventListener('click', () => {
                        const svg = chartDiv.querySelector('svg');
                        if (svg) exportSvgToPng(svg, specificFormData);
                    });
                }
            });

            lastSankeyText = JSON.stringify(data.data, null, 2);
            lastFormData = formData;
            sankeyRawText.textContent = lastSankeyText;
            sankeyRawTextContainer.style.display = 'none'; // Hide raw text for multi-view
            resultContainer.style.display = 'block';

            const initialState = document.getElementById('initialState');
            if (initialState) initialState.style.display = 'none';

        } catch (error) {
            console.error('Error:', error);
            errorMessage.textContent = error.message;
            errorMessage.style.display = 'block';
        } finally {
            submitAllBtn.disabled = false;
            submitBtn.disabled = false;
            submitAllBtn.textContent = 'Tạo 3 Báo Cáo';
        }
    });

    // --- Download Handler ---
    downloadBtn.addEventListener('click', () => {
        if (!lastSankeyText) return;
        const blob = new Blob([lastSankeyText], { type: 'text/plain' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `sankey_${lastFormData.symbol}_${lastFormData.report_type}_${lastFormData.year}.txt`;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
    });

    // --- Parser ---
    function parseSankeyData(dataText) {
        const lines = dataText.split('\n');
        const nodesMap = new Map();
        const links = [];
        let flowRow = 0; // like SankeyMATIC's sourceRow: stable input order

        lines.forEach((line) => {
            const trimmed = line.trim();
            if (!trimmed || trimmed.startsWith('//') || trimmed.startsWith(':')) return;
            const match = trimmed.match(/(.+)\s+\[([\d.]+)\]\s+(.+)/);
            if (match) {
                const source = match[1].trim();
                const value = parseFloat(match[2]);
                const target = match[3].trim();

                if (value <= 0) return;

                const sourceRow = flowRow++;

                // Keep a stable ordering hint for nodes (earliest appearance wins).
                if (!nodesMap.has(source)) nodesMap.set(source, { name: source, sourceRow });
                if (!nodesMap.has(target)) nodesMap.set(target, { name: target, sourceRow });
                nodesMap.get(source).sourceRow = Math.min(nodesMap.get(source).sourceRow, sourceRow);
                nodesMap.get(target).sourceRow = Math.min(nodesMap.get(target).sourceRow, sourceRow);

                // Add stable ordering hint for flows too (used by SankeyMATIC layout).
                links.push({ source, target, value, sourceRow });
            }
        });

        const nodes = Array.from(nodesMap.values())
            .sort((a, b) => (a.sourceRow - b.sourceRow) || String(a.name).localeCompare(String(b.name)));
        const nodeIndexMap = new Map();
        nodes.forEach((node, i) => {
            node.index = i; // Assign index to node
            nodeIndexMap.set(node.name, i);
        });

        const finalLinks = links.map((link, i) => ({
            source: nodeIndexMap.get(link.source),
            target: nodeIndexMap.get(link.target),
            value: link.value,
            index: i, // Required by SankeyMATIC's sankey.js implementation
            sourceRow: link.sourceRow
        }));

        return { nodes, links: finalLinks };
    }

    // --- Internal Rendering Engine ---
    function renderSankeyDiagram(dataText, formData, targetElement = null) {
        const container = targetElement || sankeyDiagram;
        container.innerHTML = '';
        if (typeof d3.sankey !== 'function') {
            container.innerHTML = '<p style="color:red">Lỗi: Thư viện D3 Sankey chưa được tải.</p>';
            return;
        }

        const IN = 0, OUT = 1;
        const data = parseSankeyData(dataText);
        if (data.nodes.length === 0) {
            sankeyDiagram.innerHTML = '<p style="text-align: center; color: #94a3b8; padding: 2rem;">Không tìm thấy dữ liệu.</p>';
            return;
        }

        // Layout Dimensions
        const margin = { top: 100, right: 220, bottom: 40, left: 220 };
        const width = sankeySettings.diagramWidth - margin.left - margin.right;
        const totalHeight = sankeySettings.diagramHeight - margin.top - margin.bottom;

        // --- CUSTOM SANKEY INITIALIZATION (SankeyMATIC's build/sankey.js) ---
        const sankey = d3.sankey()
            .nodeWidth(sankeySettings.nodeWidth)
            .nodeSpacingFactor(sankeySettings.nodeSpacing / 100)
            // IMPORTANT: nodeHeightFactor is already 0..1 in our state.
            // (Previously it was divided twice, which makes output look very wrong.)
            .nodeHeightFactor(sankeySettings.nodeHeightFactor)
            .size({ w: width, h: totalHeight })
            .autoLayout(true)
            .rightJustifyEndpoints(sankeySettings.rightJustifyEndpoints)
            .leftJustifyOrigins(sankeySettings.leftJustifyOrigins)
            .attachIncompletesTo('nearest');

        // Set nodes and flows (links)
        sankey.nodes(data.nodes)
            .flows(data.links);

        // Run setup and layout
        sankey.setup();
        sankey.layout(sankeySettings.layoutIterations);

        // SankeyMATIC generates "shadow" nodes/flows for layout purposes.
        // They should NOT be rendered by default (SankeyMATIC hides them too).
        const allNodes = sankey.nodes();
        const allLinks = sankey.flows();
        const nodes = allNodes.filter(n => !n.isAShadow);
        const links = allLinks.filter(l => !l.isAShadow);

        // Calculate dynamic height based on actual node positions to center labels properly
        // though the custom library already fits nodes into totalHeight.
        const svgHeight = sankeySettings.diagramHeight;

        // --- COLOR PROPAGATION ---
        const nodeColors = new Map();
        const linkColors = new Map();
        let paletteIdx = 0;
        const getNextColor = () => sankeySettings.palette[(paletteIdx++) % sankeySettings.palette.length];

        // Build adjacency only from *rendered* links (ignore shadow structure).
        const inByNode = new Map();
        const outByNode = new Map();
        nodes.forEach((n) => { inByNode.set(n.index, []); outByNode.set(n.index, []); });
        links.forEach((l) => {
            if (outByNode.has(l.source.index)) outByNode.get(l.source.index).push(l);
            if (inByNode.has(l.target.index)) inByNode.get(l.target.index).push(l);
        });

        // 1. Identify roots (nodes with no incoming rendered links)
        const roots = nodes.filter(n => (inByNode.get(n.index)?.length || 0) === 0);

        // 2. Initial coloring for roots
        roots.forEach(root => {
            if (!nodeColors.has(root.index)) nodeColors.set(root.index, getNextColor());
        });

        // 3. BFS with color splitting
        const queue = [...roots];
        const visited = new Set();

        while (queue.length > 0) {
            const curr = queue.shift();
            if (visited.has(curr.index)) continue;
            visited.add(curr.index);

            const baseColor = nodeColors.get(curr.index) || getNextColor();
            nodeColors.set(curr.index, baseColor);

            const outLinks = outByNode.get(curr.index) || [];
            outLinks.forEach((link, idx) => {
                let branchColor = (idx > 0 && outLinks.length > 1) ? getNextColor() : baseColor;
                linkColors.set(`${link.source.index}-${link.target.index}`, branchColor);

                if (!nodeColors.has(link.target.index)) {
                    nodeColors.set(link.target.index, branchColor);
                }
                queue.push(link.target);
            });
        }

        // Fallback color function
        const getColorForNode = (n) => nodeColors.get(n.index) || sankeySettings.palette[sankeySettings.palette.length - 1];
        const getColorForLink = (l) => linkColors.get(`${l.source.index}-${l.target.index}`) || getColorForNode(l.source);

        // Display formatting: round values (no decimals)
        const formatRounded = (v) => {
            const n = Number(v);
            if (!Number.isFinite(n)) return '0';
            return Math.round(n).toLocaleString('vi-VN');
        };

        // Draw SVG
        const svg = d3.select(container).append("svg")
            .attr("width", sankeySettings.diagramWidth)
            .attr("height", svgHeight)
            .append("g").attr("transform", `translate(${margin.left}, ${margin.top})`);

        // --- DRAW TITLE ON SVG ---
        const reportNames = { 'balance': 'Bảng Cân Đối Kế Toán', 'income': 'Báo Cáo Kết Quả Kinh Doanh', 'cashflow': 'Báo Cáo Lưu Chuyển Tiền Tệ' };
        const periodNames = { 'Q1': 'Quý I', 'Q2': 'Quý II', 'Q3': 'Quý III', 'Q4': 'Quý IV', 'year': 'Cả Năm' };

        const titleGrp = svg.append("g")
            .attr("transform", `translate(${width / 2}, -60)`)
            .attr("text-anchor", "middle")
            .attr("font-family", "Inter, sans-serif");

        titleGrp.append("text")
            .attr("font-size", "22px")
            .attr("font-weight", "700")
            .attr("fill", "#0f172a")
            .text(reportNames[formData.report_type] || "Biểu đồ Sankey");

        titleGrp.append("text")
            .attr("dy", "1.5em")
            .attr("font-size", "14px")
            .attr("font-weight", "400")
            .attr("fill", "#64748b")
            .text(`${formData.symbol} | ${formData.actual_period_text || (periodNames[formData.period] || formData.period) + ' ' + formData.year} | Đơn vị: Tỷ VNĐ`);

        // Flow path generator (ported from SankeyMATIC):
        // - Uses filled parallelograms for near-horizontal flows (avoids artifacts)
        // - Uses Bezier stroke for curved flows
        const flatFlowPathMaker = (f) => {
            const sx = f.source.x + f.source.dx;
            const tx = f.target.x;
            const syTop = f.source.y + f.sy;
            const tyBot = f.target.y + f.ty + f.dy;
            f.renderAs = 'flat';
            return `M${sx} ${syTop}v${f.dy}L${tx} ${tyBot}v${-f.dy}z`;
        };

        const curvedFlowPathFunction = (curvature) => (f) => {
            const syC = f.source.y + f.sy + f.dy / 2;
            const tyC = f.target.y + f.ty + f.dy / 2;
            const sEnd = f.source.x + f.source.dx;
            const tStart = f.target.x;
            if (Math.abs(syC - tyC) < 2 || Math.abs(tStart - sEnd) < 12) {
                return flatFlowPathMaker(f);
            }
            f.renderAs = 'curved';
            const xinterpolate = d3.interpolateNumber(sEnd, tStart);
            const xcp1 = xinterpolate(curvature);
            const xcp2 = xinterpolate(1 - curvature);
            return `M${sEnd} ${syC}C${xcp1} ${syC} ${xcp2} ${tyC} ${tStart} ${tyC}`;
        };

        const flowPathFn = curvedFlowPathFunction(sankeySettings.flowCurvature);

        // Draw Links
        svg.append("g")
            .attr("id", "sankey_flows")
            .selectAll("path")
            .data(links)
            .enter().append("path")
            // Sort like SankeyMATIC: largest first so smaller end up on top.
            .sort((a, b) => (b.dy - a.dy))
            .attr("d", flowPathFn)
            .attr("fill", d => (d.renderAs === 'flat' ? getColorForLink(d) : 'none'))
            .attr("stroke", d => getColorForLink(d))
            .attr("stroke-width", d => (d.renderAs === 'flat' ? 0.5 : Math.max(1, d.dy)))
            .attr("opacity", sankeySettings.flowOpacity)
            .append("title")
            .text(d => `${d.source.name} → ${d.target.name}\n${formatRounded(d.value)} tỷ`);

        // Draw Nodes
        const nodeGrp = svg.append("g").selectAll("g").data(nodes).enter().append("g");

        nodeGrp.append("rect")
            .attr("x", d => d.x)
            .attr("y", d => d.y)
            .attr("height", d => Math.max(3, d.dy))
            .attr("width", d => d.dx)
            .attr("fill", d => getColorForNode(d))
            .attr("fill-opacity", sankeySettings.nodeOpacity)
            .attr("stroke", d => d3.rgb(getColorForNode(d)).darker(1))
            .attr("stroke-width", sankeySettings.nodeBorder)
            .attr("rx", 2).attr("ry", 2)
            .append("title").text(d => `${d.name}\n${formatRounded(d.value)} tỷ`);

        // Draw Labels
        const minX = d3.min(nodes, d => d.x), maxX = d3.max(nodes, d => d.x);
        const truncate = (text, len = 35) => text.length > len ? text.substring(0, len) + "..." : text;
        const stages = d3.groups(nodes, n => n.stage);
        const maxNodesInC = d3.max(stages, s => s[1].length) || 1;

        // Label placement:
        // Prefer "outside" placement like SankeyMATIC:
        // - Origins (no incoming rendered links) => label on LEFT of node
        // - Endpoints (no outgoing rendered links) => label on RIGHT of node
        // - Otherwise fall back to first/last column, else inside/outside by midpoint
        const labelLayout = (d) => {
            const inCount = (inByNode.get(d.index)?.length || 0);
            const outCount = (outByNode.get(d.index)?.length || 0);

            // Pure origin / endpoint rules (most important for your option 1/2 toggles)
            if (inCount === 0 && outCount > 0) {
                return { x: d.x - 15, anchor: "end" };
            }
            if (outCount === 0 && inCount > 0) {
                return { x: d.x + d.dx + 15, anchor: "start" };
            }

            // Isolated node (no links): treat like origin (left)
            if (inCount === 0 && outCount === 0) {
                return { x: d.x - 15, anchor: "end" };
            }

            // Stage extremes
            if (Math.abs(d.x - minX) < 1e-6) return { x: d.x - 15, anchor: "end" };
            if (Math.abs(d.x - maxX) < 1e-6) return { x: d.x + d.dx + 15, anchor: "start" };

            // Middle columns: keep label toward the outside of the diagram
            return (d.x < width / 2)
                ? { x: d.x + d.dx + 10, anchor: "start" }
                : { x: d.x - 10, anchor: "end" };
        };

        const labelGrp = svg.append("g")
            .attr("font-family", "Inter, sans-serif")
            .selectAll("g")
            .data(nodes)
            .enter().append("g")
            .attr("transform", d => {
                const { x } = labelLayout(d);
                return `translate(${x}, ${d.y + d.dy / 2})`;
            });

        labelGrp.append("text")
            .attr("text-anchor", d => labelLayout(d).anchor)
            .attr("dy", "-0.3em")
            .attr("font-size", maxNodesInC > 20 ? "10px" : "11px")
            .attr("fill", "#64748b")
            .text(d => truncate(d.name));

        labelGrp.append("text")
            .attr("text-anchor", d => labelLayout(d).anchor)
            .attr("dy", "0.9em")
            .attr("font-size", maxNodesInC > 20 ? "11px" : "13px")
            .attr("font-weight", "700")
            .attr("fill", "#0f172a")
            .text(d => `${formatRounded(d.value)} tỷ`);
    }

    // Initial message
    sankeyDiagram.innerHTML = '<p style="text-align: center; color: #94a3b8; padding: 2rem;">Nhập mã cổ phiếu và nhấn nút để tạo biểu đồ.</p>';
});