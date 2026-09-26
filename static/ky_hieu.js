// Dòng chú thích ký hiệu trên bản đồ: chấm tròn (sự cố, xe) và ghim (điểm đi/đến).
// cacMuc: [{ kieu: 'cham' | 'ghim', mau, ten, to?: true, mo?: true }]
function veKyHieu(oChua, cacMuc) {
  const NS = 'http://www.w3.org/2000/svg';
  const tieuDe = document.createElement('b');
  tieuDe.textContent = 'Ký hiệu:';
  oChua.replaceChildren(tieuDe, ...cacMuc.map((m) => {
    const o = document.createElement('span');
    o.className = 'ky-hieu';
    let hinh;
    if (m.kieu === 'ghim') {
      hinh = document.createElementNS(NS, 'svg');
      hinh.setAttribute('viewBox', '0 0 24 32');
      hinh.setAttribute('width', '11');
      hinh.setAttribute('height', '15');
      const vo = document.createElementNS(NS, 'path');
      vo.setAttribute('d', 'M12 0C5.4 0 0 5.4 0 12c0 9 12 20 12 20s12-11 12-20C24 5.4 18.6 0 12 0z');
      vo.setAttribute('fill', m.mau);
      const tam = document.createElementNS(NS, 'circle');
      tam.setAttribute('cx', '12'); tam.setAttribute('cy', '12'); tam.setAttribute('r', '4.5');
      tam.setAttribute('fill', '#fff');
      hinh.append(vo, tam);
    } else {
      hinh = document.createElement('span');
      hinh.className = 'cham' + (m.to ? ' to' : '');
      hinh.style.background = m.mau;
      if (m.mo) hinh.style.opacity = '0.35';
    }
    o.append(hinh, document.createTextNode(m.ten));
    return o;
  }));
}
