import React from 'react';
import PropTypes from 'prop-types';
import '../index.css';

export default function Button({ children, onClick, type = 'button', disabled }) {
  return (
    <button
      type={type}
      className="button"
      onClick={onClick}
      disabled={disabled}
    >
      {children}
    </button>
  );
}

Button.propTypes = {
  children: PropTypes.node.isRequired,
  onClick: PropTypes.func,
  type: PropTypes.oneOf(['button', 'submit', 'reset']),
  disabled: PropTypes.bool,
};
