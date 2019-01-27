import { PolymerElement, html } from '@polymer/polymer/polymer-element.js';
import '@polymer/iron-flex-layout/iron-flex-layout-classes.js';
import '@polymer/iron-icons/iron-icons.js';
import '@polymer/iron-icons/editor-icons.js';
import '@polymer/paper-button/paper-button.js';
import '@polymer/paper-icon-button/paper-icon-button.js';

import './shared-styles.js';

import './homecon-page.js';
import './homecon-page-header.js';
import './homecon-web-socket-object.js';
import './homecon-state-edit.js';
import './homecon-edit-dialog.js';



class HomeconStatesList extends PolymerElement {
  static get template() {
    return html`
      <style include="shared-styles iron-flex iron-flex-alignment">
        :host{
          display: block;
          padding-left: 10px;
        }
        div.state{
          font-weight: 500;
          margin-top: 10px;
        }
        div.state:hover .controls{
          display: inline;
        }
        .controls {
          display: none;
          margin-left: 16px;
        }
        .controls paper-icon-button{
          padding: 0px;
          height: 22px;
          width: 22px;
          margin-left: 10px;
        }
      </style>

      <homecon-web-socket-object event="state_children" key="{{key}}" data="{{states}}" auto>
      </homecon-web-socket-object>

      <template is="dom-repeat" items="{{states}}" as="state">
        <div class="state">
          <span>/{{state.name}}</span>
          <span class="controls">
            <paper-icon-button icon="editor:mode-edit" noink="true" on-tap="openEditDialog"></paper-icon-button>
            <paper-icon-button icon="icons:add" noink="true" on-tap="openAddDialog"></paper-icon-button>
          </paper-icon-button></span>
        </div>
        <homecon-states-list key="{{state.id}}"></homecon-states-list>
      </template>



      <homecon-edit-dialog id="editStateDialog">
        test
      </homecon-edit-dialog>
    `;
  }

  static get properties() {
    return {
      key: {
        type: Number,
      },
    };
  }

  openEditDialog(e){
    //this.$.editState.oldState = e.model.__data.state;
    this.$.editStateDialog.open();
  }

  openAddDialog(e){
    //this.$.editState.oldState = null;
    //this.$.editState.newParent = e.model.__data.state.id
    this.$.editStateDialog.open();
  }

}

window.customElements.define('homecon-states-list', HomeconStatesList);


class HomeconStateListState extends PolymerElement {
  static get template() {
    return html`
      <style include="shared-styles iron-flex iron-flex-alignment">
        :host{
          display: block;
        }
        div.state{
          font-weight: 500;
          margin-top: 10px;
        }
        div.state:hover .controls{
          display: inline;
        }
        .controls {
          display: none;
          margin-left: 16px;
        }
        .controls paper-icon-button{
          padding: 0px;
          height: 22px;
          width: 22px;
          margin-left: 10px;
        }
      </style>

      <homecon-web-socket-object event="state" key="{{key}}" data="{{state}}" auto>
      </homecon-web-socket-object>

      <div class="state">
        <span>{{state.path}}</span>
        <span class="controls">
          <paper-icon-button icon="editor:mode-edit" noink="true" on-tap="openEditDialog"></paper-icon-button>
          <paper-icon-button icon="icons:add" noink="true" on-tap="openAddDialog"></paper-icon-button>
        </paper-icon-button></span>
      </div>
    `;
  }

  static get properties() {
    return {
      key: {
        type: Number,
      },
    };
  }

  openEditDialog(e){
    this.dispatchEvent(new CustomEvent('open-edit-dialog', {'detail': {'state': this.state}}));
  }

  openAddDialog(e){
    this.dispatchEvent(new CustomEvent('open-add-dialog', {'detail': {'parent': this.key}}));
  }

}

window.customElements.define('homecon-states-list-state', HomeconStateListState);


class ViewStates extends PolymerElement {
  static get template() {
    return html`
      <style include="shared-styles">
        :host {
          display: block;
        }
        div.state{
          font-weight: 500;
          margin-top: 10px;
        }
        div.state:hover .controls{
          display: inline;
        }
        .controls {
          display: none;
          margin-left: 16px;
        }
        .controls paper-icon-button{
          padding: 0px;
          height: 22px;
          width: 22px;
          margin-left: 10px;
        }
      </style>


      <homecon-web-socket-object event="state_list" key="" data="{{states}}" auto>
      </homecon-web-socket-object>

      <homecon-page>
        <homecon-page-header title="States" icon="edit_settings"></homecon-page-header>

        <div id="content" class="raised">

          <template is="dom-repeat" items="{{states}}" as="state" sort="_sort">
            <homecon-states-list-state key="{{state.id}}" on-open-edit-dialog="openEditDialog" on-open-add-dialog="openAddDialog">
            </homecon-states-list-state>

            <!--<div class="state">
              <span>{{state.path}}</span>
              <span class="controls">
                <paper-icon-button icon="editor:mode-edit" noink="true" on-tap="openEditDialog"></paper-icon-button>
                <paper-icon-button icon="icons:add" noink="true" on-tap="openAddDialog"></paper-icon-button>
              </paper-icon-button></span>

            </div>-->
          </template>

        </div>

        <homecon-edit-dialog id="editStateDialog" on-save="_saveState" on-cancel="closeEditDialog">
          <homecon-state-edit id="editState"></homecon-state-edit>
        </homecon-edit-dialog>

      </homecon-page>
    `;
  }

  openEditDialog(e){
    this.$.editState.oldState = e.detail.state;
    this.$.editStateDialog.open();
  }

  openAddDialog(e){
    this.$.editState.oldState = null;
    this.$.editState.newParent = e.detail.parent
    this.$.editStateDialog.open();
  }

  _saveState(e){
    this.$.editState.save()
  }

  _sort(a, b){
    return a-b
  }
}

window.customElements.define('view-states', ViewStates);
